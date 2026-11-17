"""wfj voice: the Italian voice over of the NPCs. This module builds who speaks each line; the casting verbs
(profiles, cast) are in `voice_cast`, the pilot's scope list in `voice_scope`.

  speakers --vmangos FILE --commit SHA --scope NAME [--forever-vo DIR --forever-vo-commit SHA]
           [--vmangos-src DIR]
      Writes data/voice/speakers.jsonl (pack key → its main speaker, a creature id, `narrator` or
      `book-narrator`, and the `others` who say it too) for the scope's quests, the NPC talk of their givers
      and takers, and the scope's book pages. From the VMaNGOS world database, the creature ids the
      collector recorded with gossip English (data/english/gossip `npcs`, which win) and, with --forever-vo,
      the players' captures for the quests the database lacks. Scope `tutto` adds every NPC's greeting, the
      NPC lines in chat (`s-`: the database's scripts and, with --vmangos-src, the core's C++ ones) and the
      intro subtitles (`i-`, pipeline/voice_intros.tsv: each race's narrator). Prints the lines read by a
      narrator, the counts by kind, the conflicts and the scoped lines with no Italian.
  profiles build|export|import, cast        see `voice_cast`
  scope NAME --vmangos FILE                 see `voice_scope`
  plan, generate, status                    see `voice_make`
  spoken export|import                      see `voice_spoken`
  audition                                  see `voice_audition`
  pack                                      see `voice_ship`
  design                                    see `voice_design`
  candidates                                see `voice_candidates`
  batch submit|fetch|cancel                 see `voice_batch`
"""

from __future__ import annotations

import argparse
import datetime
import importlib
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from wfj.core import voice
from wfj.emit.lua_writer import shipped
from wfj.io import forever_vo, vmangos, vmangos_src
from wfj.io.jsonl_store import Store, dumps
from wfj.paths import data_root

# the BroadcastText id ranges of each race's intro cinematic subtitles (first, last, race)
INTROS = Path("pipeline") / "voice_intros.tsv"
INTRO_ROW = re.compile(r"BroadcastText:\d+")
# the scope whose speakers are the whole game's: every NPC's greeting, the lines in chat, the intros
EVERYONE = "tutto"


def voice_dir(root: Path) -> Path:
    return root / "voice"


def today() -> str:
    return datetime.date.today().isoformat()


def scope_path(root: Path, scope: str) -> Path:
    """The file listing a scope's quests and book pages (`voice.read_scope_file`)."""
    return root.parent / voice.SCOPES[scope]


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(raw) for raw in f if raw.strip()]


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(dumps(r) + "\n" for r in rows), encoding="utf-8")


def keep_dates(rows: list[dict[str, Any]], old: list[dict[str, Any]], id_field: str) -> list[dict[str, Any]]:
    """A row unchanged but for its date keeps its old date: a re-run on another day writes the same bytes."""
    before = {r[id_field]: r for r in old}
    out = []
    for r in rows:
        prev = before.get(r[id_field])
        same = prev and {**prev, "provenance": {**prev["provenance"], "imported": ""}} == {
            **r, "provenance": {**r["provenance"], "imported": ""}
        }
        out.append(prev if same else r)
    return out


def book_hashes(root: Path) -> dict[int, str]:
    """page id → the English hash that keys it (a book page's pack key is `b-<hash>`)."""
    return {int(ln["id"]): str(ln["hash"]) for ln in Store(root, english=True).load("book") if ln.get("hash")}


def shipped_lines(root: Path, quests: Sequence[int], books: Sequence[str]) -> dict[str, str]:
    """{pack key: shipped Italian} for the quests' voiced fields, every shipped gossip line (the speakers
    table narrows gossip to the scope's creatures) and the book pages."""
    store = Store(root)
    want = set(quests)
    out = {
        voice.quest_key(ln["id"], ln["field"]): ln["it"]
        for ln in store.load("quest")
        if ln["id"] in want and ln["field"] in voice.FIELDS and shipped(ln)
    }
    gossip = [ln for ln in store.load("gossip") if shipped(ln)]
    out.update({voice.gossip_key(ln["id"]): ln["it"] for ln in gossip})
    # an NPC's line in chat is a gossip line too (the same key): the speakers table holds only the said ones
    out.update({voice.speech_key(ln["id"]): ln["it"] for ln in gossip})
    # an intro's subtitle: a BroadcastText row of the UI
    out.update({
        voice.intro_key(int(ln["id"].split(":", 1)[1])): ln["it"]
        for ln in store.load("ui")
        if INTRO_ROW.fullmatch(str(ln["id"])) and shipped(ln)
    })
    hashes, pages = book_hashes(root), set(books)
    # pages sharing one English: the addon ships the lowest page id's Italian (`lua_writer.keyed_rows`)
    for ln in sorted(store.load("book"), key=lambda ln: ln["id"]):
        if shipped(ln) and hashes.get(ln["id"]) in pages:
            out.setdefault(voice.book_key(hashes[ln["id"]]), ln["it"])
    return out


def read_intros(root: Path) -> dict[int, str]:
    """BroadcastText id → the intro narrator who reads it, from pipeline/voice_intros.tsv (first, last, race;
    the ids of each race's intro subtitles). No table, no intro lines."""
    path = root.parent / INTROS
    if not path.is_file():
        return {}
    out: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith(("#", "first\t")):
            continue
        first, last, race = raw.split("\t")
        narrator = f"narrator-{race}"
        if narrator not in voice.INTRO_NARRATORS:
            raise ValueError(f"{INTROS}: unknown race {race!r}")
        out.update({i: narrator for i in range(int(first), int(last) + 1)})
    return out


Said = list[tuple[int, str]]  # (creature id, English)


def speech_lines(db: Path, core: Path | None) -> tuple[Said, Said, list[str]]:
    """(lines the database's scripts give their creatures, lines the core's C++ scripts give theirs, report);
    without `core` the C++ ones are none."""
    said = vmangos.read_speech_speakers(db)
    if core is None:
        return said, [], []
    pairs, report = vmangos_src.read_script_speech(core, vmangos.read_script_names(db))
    texts = vmangos.read_broadcast_texts(db, {b for _, b in pairs})
    return said, sorted({(c, t) for c, b in pairs for t in texts.get(b, ())}), report


def chat_speakers(  # noqa: PLR0913 - the collector's two tables travel together
    said_db: Said, said_core: Said, commit: str,
    collector: tuple[dict[str, list[int]], dict[str, str]], shipped_keys: set[str],
    others: dict[str, list[int]],
) -> dict[str, tuple[int, str]]:
    """{`s-` pack key: (speaker, provenance source)} for the NPC lines in chat that ship Italian, chosen like
    a greeting's (the collector's creature wins, else the lowest; the rest go to `others`)."""
    npcs, npcs_src = collector
    from_core = {(c, voice.gossip_id(t)) for c, t in said_core}
    found_others: dict[str, list[int]] = {}
    found, _ = voice.gossip_speakers(said_db + said_core, npcs, shipped_keys, found_others)
    out: dict[str, tuple[int, str]] = {}
    for g, c in found.items():
        k, key = g[2:], voice.speech_key(g[2:])
        if found_others.get(g):
            others[key] = found_others[g]
        source = (npcs_src[k] if c in npcs.get(k, []) else
                  f"vmangos-src@{commit}" if (c, k) in from_core else f"vmangos@{commit}")
        out[key] = (c, source)
    return out


def build_tables(  # noqa: PLR0913 - the whole game's sources are keywords
    root: Path, db: Path, commit: str, scope: tuple[Sequence[int], Sequence[str]], today: str,
    captures: tuple[Path, str] | None = None, *, everyone: bool = False, core: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """(speakers rows, report) for a scope's (quest ids, book keys). A speakers row names the line's main
    speaker and, when several creatures say it, the `others` (each may be cast to a voice of its own).
    `everyone` (the whole game): every creature with a gossip menu, a quest window greeting or a line the
    collector heard greets, not only the scope's quest NPCs; the NPC lines in chat get their speakers (from
    the database's scripts and, with `core`, the core's C++ ones) and the intro subtitles their race's
    narrator."""
    quests, books = set(scope[0]), list(scope[1])
    src = f"vmangos@{commit}"
    store, english_store = Store(root), Store(root, english=True)
    lines = shipped_lines(root, sorted(quests), books)
    quest_keys = [k for k in lines if k[0].isdigit()]
    starters, objects, enders = vmangos.read_quest_speakers(db, quests)
    others: dict[str, list[int]] = {}
    q_speakers, q_problems = voice.quest_speakers(quest_keys, starters, objects, enders, others)
    # a quest the open database lacks (one Forever added): who the players' captures saw in the window
    captured_src: dict[str, str] = {}
    if captures is not None:
        seen = forever_vo.read_quest_speakers(captures[0])
        for key, sp in q_speakers.items():
            q, f = key.split("-", 1)
            who = voice.captured_speaker(seen.get((int(q), f), []))
            if sp == voice.NARRATOR and who is not None:
                q_speakers[key] = who
                captured_src[key] = f"forever-vo@{captures[1]}"
        q_problems = [p for p in q_problems if p.split(":", 1)[0] not in captured_src]
    creatures = {c for q in quests for c in (*starters.get(q, ()), *enders.get(q, ()))}
    creatures |= {s for s in q_speakers.values() if isinstance(s, int)}
    gossip_shipped = {ln["id"] for ln in store.load("gossip") if shipped(ln)}
    english_gossip = english_store.load("gossip")
    collector = {ln["id"]: ln["npcs"] for ln in english_gossip if ln.get("npcs")}
    collector_src = {ln["id"]: ln["src"] for ln in english_gossip if ln.get("npcs")}
    if everyone:  # every NPC that greets, not only the quests' ones
        creatures |= vmangos.read_gossip_creatures(db) | {int(n) for npcs in collector.values() for n in npcs}
    said = vmangos.read_creature_lines(db, creatures)
    # a line the client served with one of these creatures, whether or not the database has it
    said += [(n, ln["en"]) for ln in english_gossip for n in ln.get("npcs") or () if n in creatures]
    g_speakers, report = voice.gossip_speakers(said, collector, gossip_shipped, others)
    report["quest"] = q_problems
    s_speakers: dict[str, tuple[int, str]] = {}
    report["speech"] = []
    if everyone:
        said_db, said_core, report["speech"] = speech_lines(db, core)
        s_speakers = chat_speakers(said_db, said_core, commit, (collector, collector_src), gossip_shipped,
                                   others)
    have_english = {(ln["id"], ln["field"]) for ln in english_store.load("quest")}
    report["missing"] += sorted(
        voice.quest_key(q, f)
        for q in quests
        for f in voice.FIELDS
        if voice.quest_key(q, f) not in lines and (q, f) in have_english
    )
    report["missing"] += [voice.book_key(b) for b in sorted(books) if voice.book_key(b) not in lines]

    def row(key: str, speaker: int | str, source: str) -> dict[str, Any]:
        r: dict[str, Any] = {"key": key, "speaker": speaker}
        if others.get(key):
            r["others"] = others[key]
        r["provenance"] = {"source": source, "imported": today}
        return r

    speakers = [row(k, s, captured_src.get(k, src)) for k, s in sorted(q_speakers.items())]
    speakers += [
        row(k, s, collector_src[k[2:]] if s in collector.get(k[2:], []) else src)
        for k, s in sorted(g_speakers.items())
    ]
    speakers += [row(k, s, source) for k, (s, source) in sorted(s_speakers.items())]
    if everyone:  # each intro subtitle shipped in Italian: its race's narrator
        speakers += [row(voice.intro_key(b), who, f"intro@{INTROS.name}")
                     for b, who in sorted(read_intros(root).items()) if voice.intro_key(b) in lines]
    # each book page: its signer if one creature that speaks has that name, else the book narrator
    speaking = {c for r in speakers for c in (r["speaker"], *r.get("others", ())) if isinstance(c, int)}
    speaking |= {int(r["creature"]) for r in read_rows(voice_dir(root) / "voices.jsonl")}
    english_pages = {str(ln["hash"]): ln["en"] for ln in english_store.load("book") if ln.get("hash")}
    pages = {voice.book_key(b): english_pages.get(b, "") for b in books if voice.book_key(b) in lines}
    names: dict[str, list[int]] = {}
    if pages:
        for c, info in vmangos.read_creatures(db).items():
            names.setdefault(str(info["name"]), []).append(c)
    for k, who in voice.book_speakers(pages, names, speaking).items():
        source = "book@narrator" if who == voice.BOOK_NARRATOR else f"book-signature@{commit}"
        speakers.append(row(k, who, source))
    speakers.sort(key=lambda r: r["key"])
    return speakers, report


def keep_speakers(rows: list[dict[str, Any]], old: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A line whose old main speaker still says it keeps that speaker (its audio was made in that voice):
    widening the scope adds creatures to a line and the lowest would otherwise take it over. The new main
    speaker joins the `others`."""
    before = {r["key"]: r["speaker"] for r in old}
    out = []
    for r in rows:
        was = before.get(r["key"])
        rest = r.get("others", [])
        keep = isinstance(was, int) and was != r["speaker"] and was in rest
        out.append({**r, "speaker": was, "others": sorted({*rest, r["speaker"]} - {was})} if keep else r)
    return out


def run_speakers(a: argparse.Namespace) -> int:
    root = data_root()
    if a.forever_vo and not Path(a.forever_vo).is_dir():
        raise FileNotFoundError(f"--forever-vo {a.forever_vo}: no such folder (its captures name givers)")
    scope = voice.read_scope_file(scope_path(root, a.scope))
    speakers, report = build_tables(
        root, Path(a.vmangos), a.commit, scope, today(),
        (Path(a.forever_vo), a.forever_vo_commit) if a.forever_vo else None,
        everyone=a.scope == EVERYONE, core=Path(a.vmangos_src) if a.vmangos_src else None,
    )
    d = voice_dir(root)
    old = read_rows(d / "speakers.jsonl")
    speakers = keep_dates(keep_speakers(speakers, old), old, "key")
    write_rows(d / "speakers.jsonl", speakers)
    narrator = [r["key"] for r in speakers if r["speaker"] in (voice.NARRATOR, voice.BOOK_NARRATOR)]
    creatures = {c for r in speakers for c in (r["speaker"], *r.get("others", ())) if isinstance(c, int)}
    several = sum("others" in r for r in speakers)
    print(f"voice speakers: {len(speakers)} lines, {len(creatures)} creatures → data/voice/speakers.jsonl")
    print(f"voice speakers: {len(narrator)} narrator lines")
    print(f"voice speakers: {several} lines with several speakers")
    for prefix, what in (("g-", "greetings"), ("s-", "lines in chat"), ("i-", "intro lines")):
        print(f"voice speakers: {sum(r['key'].startswith(prefix) for r in speakers)} {what}")
    print(f"voice speakers: {len(report.get('speech', []))} C++ lines left out (no single script uses them)")
    for name in ("quest", "conflict", "missing"):
        for item in report.get(name, []):
            print(f"voice speakers: {name}: {item}")
    return 0


OWN_MODULE = {
    "scope": "voice_scope", "audition": "voice_audition", "spoken": "voice_spoken", "pack": "voice_ship",
    "design": "voice_design", "candidates": "voice_candidates",
    "batch": "voice_batch",
}


def run(argv: Sequence[str]) -> int:
    verb = list(argv[:1])
    if verb == ["profiles"]:
        from wfj.cmd import voice_cast  # the casting verbs live in their own module

        return voice_cast.run_profiles(argv[1:])
    if verb == ["cast"]:
        from wfj.cmd import voice_cast

        return voice_cast.run_cast(argv[1:])
    if verb and verb[0] in ("plan", "generate", "status"):
        from wfj.cmd import voice_make  # the audio files

        return voice_make.run(argv)
    if verb and verb[0] in OWN_MODULE:  # each of these lives in its own module, loaded only when asked for
        return importlib.import_module(f"wfj.cmd.{OWN_MODULE[verb[0]]}").run(argv[1:])
    p =argparse.ArgumentParser(prog="wfj voice")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("speakers")
    sp.add_argument("--vmangos", required=True)
    sp.add_argument("--commit", required=True)
    sp.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
    sp.add_argument("--forever-vo", help="forever-vo, pinned: who speaks quests the database lacks")
    sp.add_argument("--forever-vo-commit", default="")
    sp.add_argument("--vmangos-src", help="vmangos/core at the database's commit: who says the C++ lines")
    a = p.parse_args(list(argv))
    try:
        return run_speakers(a)
    except (ValueError, FileNotFoundError, vmangos.VmangosError) as e:
        print(f"voice {a.cmd}: {e}", file=sys.stderr)
        return 1
