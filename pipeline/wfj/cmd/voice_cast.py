"""wfj voice profiles build|export|import and wfj voice cast: who each speaking creature is, and which Gemini
voice reads it.

  profiles build --vmangos FILE --commit SHA --client DIR
      Writes data/voice/profiles.jsonl: one row per creature that speaks a line in data/voice/speakers.jsonl,
      with what the client's display tables (DIR, `make tables-extract`) and VMaNGOS say (race, gender, the
      kind of being, a racial leader's role). Values from the casting pass and the rulings already in the
      file are kept (core/casting.build).
  profiles export --vmangos FILE --out DIR [--per N]
      Writes the casting pass's input: part-NN.jsonl files of the speakers that still need judgement, each
      with its name, title, creature type, what the tables say and up to three of its Italian lines.
  profiles import --drafts FILE… --model ID --batch NAME
      Merges the pass's drafts into data/voice/profiles.jsonl (never over a table value or a ruling) and
      prints the speakers still owed an age.
  cast --scope NAME [--config pipeline/voice.toml]
      Writes data/voice/voices.jsonl: the roster voice of every profiled creature that speaks a line of the
      scope, by the first matching cast row of voice.toml (data/voice/overrides.jsonl rulings win). The same
      creature always gets the same voice.
"""

from __future__ import annotations

import argparse
import datetime
import sys
import tomllib
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from wfj.cmd.voice import read_rows as _rows
from wfj.cmd.voice import scope_path
from wfj.cmd.voice import write_rows as _write
from wfj.core import casting, voice
from wfj.emit.lua_writer import shipped
from wfj.io import client_tables, vmangos
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

PROFILES = "profiles.jsonl"
VOICES = "voices.jsonl"
CONFIG = Path("pipeline") / "voice.toml"
TYPE_NAMES = {
    1: "beast",
    2: "dragonkin",
    3: "demon",
    4: "elemental",
    5: "giant",
    6: "undead",
    7: "humanoid",
    8: "critter",
    9: "mechanical",
    10: "not specified",
}
LINES_PER_SPEAKER = 3


def load_config(path: Path) -> dict[str, Any]:
    """voice.toml, checked (`casting.roster_problems`), with each roster voice as the engine and
    `voice.in_step` read it: {gemini_voice, model, notes, fits}. Raises ValueError listing every problem."""
    with path.open("rb") as f:
        cfg = tomllib.load(f)
    raw, cfg["cast"] = cfg.get("roster", {}), cfg.get("cast", [])
    narrators = cfg.get("narrator", ""), cfg.get("book_narrator", "")
    problems = casting.roster_problems(raw, cfg["cast"], *narrators)
    if not isinstance(cfg.get("model"), str) or not cfg["model"]:
        problems.append("model must name the Gemini TTS model")
    if problems:
        raise ValueError(f"{path.name}: " + "; ".join(problems))
    cfg["roster"] = {
        vid: {"gemini_voice": v["voice"], "model": cfg["model"], "notes": v["notes"],
              "fits": v.get("fits", "")}
        for vid, v in raw.items()
    }
    return cfg


def speaking(root: Path, rows: Sequence[dict[str, Any]] | None = None) -> set[int]:
    """Every creature the speakers rows name, main speaker or other (default: data/voice/speakers.jsonl)."""
    if rows is None:
        rows = _rows(root / "voice" / "speakers.jsonl")
    return {c for r in rows for c in (r["speaker"], *r.get("others", ())) if isinstance(c, int)}


def build(root: Path, db: Path, commit: str, client: Path, today: str) -> tuple[list[dict[str, Any]], dict]:
    who = speaking(root)
    creatures = vmangos.read_creatures(db, who)
    displays, client_src = client_tables.read_displays(client)
    vm_genders = vmangos.read_creature_genders(db, who)
    vm_src = f"vmangos@{commit}"
    table_facts = {
        c: casting.facts(creatures.get(c), displays, client_src, vm_src, vm_genders.get(c)) for c in who
    }
    rows = casting.build(who, table_facts, _rows(root / "voice" / PROFILES), today)
    stats = {
        "speakers": len(who),
        "not in the database": sum(c not in creatures for c in who),
        **{f"{f} from the tables": sum(f in table_facts[c] for c in who) for f in casting.FIELDS},
        "still need judgement": sum(bool(casting.needs_judgement(r)) for r in rows),
    }
    return rows, stats


def _lines_by_speaker(root: Path) -> dict[int, list[str]]:
    """creature → the shipped Italian of the lines it speaks, longest first (the pass reads up to three)."""
    store = Store(root)
    it = {voice.quest_key(ln["id"], ln["field"]): ln["it"] for ln in store.load("quest") if shipped(ln)}
    it.update({voice.gossip_key(ln["id"]): ln["it"] for ln in store.load("gossip") if shipped(ln)})
    out: dict[int, list[str]] = {}
    for r in _rows(root / "voice" / "speakers.jsonl"):
        for c in (r["speaker"], *r.get("others", ())):
            if isinstance(c, int) and r["key"] in it:
                out.setdefault(c, []).append(it[r["key"]])
    return {c: sorted(set(v), key=lambda t: (-len(t), t)) for c, v in out.items()}


def export(root: Path, db: Path, out: Path, per: int) -> int:
    """The casting pass's input files. → how many speakers were exported."""
    rows = _rows(root / "voice" / PROFILES)
    want = [r for r in rows if casting.needs_judgement(r)]
    creatures = vmangos.read_creatures(db, {r["creature"] for r in want})
    names = {r["id"]: r["en"] for r in Store(root, english=True).load("unit") if r.get("field") == "name"}
    lines = _lines_by_speaker(root)
    items = []
    for r in want:
        c = r["creature"]
        cr = creatures.get(c) or {}
        items.append(
            {
                "creature": c,
                "name": cr.get("name") or names.get(c, ""),
                "title": cr.get("subname", ""),
                "type": TYPE_NAMES.get(int(cr.get("type", 0) or 0), "unknown"),
                "known": {
                    f: r[f]
                    for f in casting.FIELDS
                    if r.get(f) is not None and f not in casting.needs_judgement(r)
                },
                "lines": [t[:400] for t in lines.get(c, [])[:LINES_PER_SPEAKER]],
            }
        )
    out.mkdir(parents=True, exist_ok=True)
    for n in range(0, len(items), per):
        _write(out / f"part-{n // per + 1:02d}.jsonl", items[n : n + per])
    return len(items)


def import_drafts(root: Path, files: Sequence[Path], model: str, batch: str, today: str) -> list[str]:
    path = root / "voice" / PROFILES
    drafts = [d for f in files for d in _rows(f)]
    rows, problems = casting.merge_machine(_rows(path), drafts, model, batch, today)
    _write(path, rows)
    return problems


def run_profiles(argv: Sequence[str]) -> int:
    p = argparse.ArgumentParser(prog="wfj voice profiles")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--vmangos", required=True)
    b.add_argument("--commit", required=True)
    b.add_argument("--client", required=True, help="the client folder holding the display tables")
    e = sub.add_parser("export")
    e.add_argument("--vmangos", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--per", type=int, default=800)
    i = sub.add_parser("import")
    i.add_argument("--drafts", nargs="+", required=True)
    i.add_argument("--model", required=True)
    i.add_argument("--batch", required=True)
    a = p.parse_args(list(argv))
    root = data_root()
    today = datetime.date.today().isoformat()
    try:
        if a.cmd == "build":
            rows, stats = build(root, Path(a.vmangos), a.commit, Path(a.client), today)
            _write(root / "voice" / PROFILES, rows)
            print(f"voice profiles: {len(rows)} speakers → data/voice/{PROFILES}")
            for k, v in stats.items():
                print(f"voice profiles: {k}: {v}")
        elif a.cmd == "export":
            n = export(root, Path(a.vmangos), Path(a.out), a.per)
            print(f"voice profiles: {n} speakers to judge → {a.out}")
        else:
            problems = import_drafts(root, [Path(f) for f in a.drafts], a.model, a.batch, today)
            for pr in problems:
                print(f"voice profiles: {pr}")
            owed = casting.missing_age(_rows(root / "voice" / PROFILES))
            print(f"voice profiles: {len(problems)} problem(s); {len(owed)} speaker(s) still owed an age")
            return 1 if owed else 0
    except (ValueError, FileNotFoundError, vmangos.VmangosError) as e:
        print(f"voice profiles: {e}", file=sys.stderr)
        return 1
    return 0


def in_scope(
    rows: Sequence[dict[str, Any]], quests: Sequence[int], books: Sequence[str]
) -> list[dict[str, Any]]:
    """The speakers rows of a scope: its quests' fields, its book pages and the NPC talk (the table holds the
    talk of the scope's creatures only)."""
    want, pages = set(quests), {voice.book_key(b) for b in books}
    return [
        r for r in rows
        if (r["key"][0].isdigit() and int(r["key"].split("-", 1)[0]) in want)
        or r["key"] in pages
        or r["key"].startswith("g-")
    ]


def cast_rows(root: Path, cfg: dict[str, Any], scope: str, today: str) -> list[dict[str, Any]]:
    """voices.jsonl rows for the profiled creatures that speak in the scope, from the cast rows and the
    overrides. A row whose voice and cast row are unchanged keeps its old date."""
    quests, books = voice.read_scope_file(scope_path(root, scope))
    who = speaking(root, in_scope(_rows(root / "voice" / "speakers.jsonl"), quests, books))
    profiles = [p for p in _rows(root / "voice" / PROFILES) if int(p["creature"]) in who]
    overrides = {int(r["creature"]): r["voice"] for r in _rows(root / "voice" / "overrides.jsonl")}
    result = casting.cast(profiles, cfg["cast"], cfg["narrator"], overrides)
    old = {int(r["creature"]): r for r in _rows(root / "voice" / VOICES)}
    rows = []
    for c, v in sorted(result.items()):
        row: dict[str, Any] = {"creature": c, **v}
        prev = old.get(c)
        same = prev and {k: prev.get(k) for k in v} == v and set(prev) - {"creature", "provenance"} == set(v)
        row["provenance"] = prev["provenance"] if same else {"source": "cast@voice.toml", "imported": today}
        rows.append(row)
    return rows


def run_cast(argv: Sequence[str]) -> int:
    p = argparse.ArgumentParser(prog="wfj voice cast")
    p.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
    p.add_argument("--config", default=None, help="voice.toml (default: pipeline/voice.toml)")
    a = p.parse_args(list(argv))
    root = data_root()
    try:
        cfg = load_config(Path(a.config) if a.config else root.parent / CONFIG)
        rows = cast_rows(root, cfg, a.scope, datetime.date.today().isoformat())
    except (ValueError, FileNotFoundError) as e:
        print(f"voice cast: {e}", file=sys.stderr)
        return 1
    _write(root / "voice" / VOICES, rows)
    print(f"voice cast: {len(rows)} creatures → data/voice/{VOICES}")
    for name, n in Counter(r["row"] for r in rows).most_common():
        print(f"voice cast: {n:5d}  {name}")
    return 0
