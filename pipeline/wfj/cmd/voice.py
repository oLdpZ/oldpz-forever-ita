"""wfj voice: the Italian voice over of the NPCs. This module builds who speaks each line; the casting verbs
(profiles, cast) are in `voice_cast`, the pilot's scope list in `voice_scope`.

  speakers --vmangos FILE --commit SHA --scope NAME [--forever-vo DIR --forever-vo-commit SHA]
      Writes data/voice/speakers.jsonl (pack key → its main speaker, a creature id, `narrator` or
      `book-narrator`, and the `others` who say it too) for the scope's quests, the NPC talk of their givers
      and takers, and the scope's book pages. From the VMaNGOS world database, the creature ids the
      collector recorded with gossip English (data/english/gossip `npcs`, which win) and, with --forever-vo,
      the players' captures for the quests the database lacks. Prints the lines read by a narrator, the
      conflicts and the scoped lines with no Italian.
  profiles build|export|import, cast        see `voice_cast`
  scope NAME --vmangos FILE                 see `voice_scope`
  plan, generate, status                    see `voice_make`
  spoken export|import                      see `voice_spoken`
  audition                                  see `voice_audition`
  pack                                      see `voice_ship`
  design                                    see `voice_design`
"""

from __future__ import annotations

import argparse
import datetime
import importlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from wfj.core import voice
from wfj.emit.lua_writer import shipped
from wfj.io import forever_vo, vmangos
from wfj.io.jsonl_store import Store, dumps
from wfj.paths import data_root


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
    out.update({voice.gossip_key(ln["id"]): ln["it"] for ln in store.load("gossip") if shipped(ln)})
    hashes, pages = book_hashes(root), set(books)
    # pages sharing one English: the addon ships the lowest page id's Italian (`lua_writer.keyed_rows`)
    for ln in sorted(store.load("book"), key=lambda ln: ln["id"]):
        if shipped(ln) and hashes.get(ln["id"]) in pages:
            out.setdefault(voice.book_key(hashes[ln["id"]]), ln["it"])
    return out


def build_tables(
    root: Path, db: Path, commit: str, scope: tuple[Sequence[int], Sequence[str]], today: str,
    captures: tuple[Path, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """(speakers rows, report) for a scope's (quest ids, book keys). A speakers row names the line's main
    speaker and, when several creatures say it, the `others` (each may be cast to a voice of its own)."""
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
    said = vmangos.read_creature_lines(db, creatures)
    # a line the client served with one of these creatures, whether or not the database has it
    said += [(n, ln["en"]) for ln in english_gossip for n in ln.get("npcs") or () if n in creatures]
    g_speakers, report = voice.gossip_speakers(said, collector, gossip_shipped, others)
    report["quest"] = q_problems
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


def run_speakers(a: argparse.Namespace) -> int:
    root = data_root()
    scope = voice.read_scope_file(scope_path(root, a.scope))
    speakers, report = build_tables(
        root, Path(a.vmangos), a.commit, scope, today(),
        (Path(a.forever_vo), a.forever_vo_commit) if a.forever_vo else None,
    )
    d = voice_dir(root)
    speakers = keep_dates(speakers, read_rows(d / "speakers.jsonl"), "key")
    write_rows(d / "speakers.jsonl", speakers)
    narrator = [r["key"] for r in speakers if r["speaker"] in (voice.NARRATOR, voice.BOOK_NARRATOR)]
    creatures = {c for r in speakers for c in (r["speaker"], *r.get("others", ())) if isinstance(c, int)}
    several = sum("others" in r for r in speakers)
    print(f"voice speakers: {len(speakers)} lines, {len(creatures)} creatures → data/voice/speakers.jsonl")
    print(f"voice speakers: {len(narrator)} narrator lines")
    print(f"voice speakers: {several} lines with several speakers")
    for name in ("quest", "conflict", "missing"):
        for item in report.get(name, []):
            print(f"voice speakers: {name}: {item}")
    return 0


OWN_MODULE = {
    "scope": "voice_scope", "audition": "voice_audition", "spoken": "voice_spoken", "pack": "voice_ship",
    "design": "voice_design",
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
    a = p.parse_args(list(argv))
    try:
        return run_speakers(a)
    except (ValueError, FileNotFoundError, vmangos.VmangosError) as e:
        print(f"voice {a.cmd}: {e}", file=sys.stderr)
        return 1
