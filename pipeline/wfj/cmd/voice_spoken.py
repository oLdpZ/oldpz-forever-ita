"""wfj voice spoken export|import: the spoken versions, what the voice says for a line it cannot say as
written.

Two kinds of line need one: a line naming the player's class or race (`{class}`, `{race}`: the pack is made
before anyone plays, and a fixed word would break the grammar), and a line whose every take the safety filter
blocked. Its spoken version keeps the sense, lightly reworded. It is kept per line beside the hash of the
written Italian, so a changed translation makes it stale (never read again until it is written anew).

  export --scope S --out FILE [--store DIR] [--config F]
      Writes FILE (JSONL), one row per line of the scope that needs a spoken version and has none in step:
      {key, sex, it_hash, it, spoken, reason[, stale]}. `sex` is `any` for a version both sexes hear, `m` or
      `f` for a take blocked for one sex; a stale version is offered again in `spoken`, to revise. Blocked
      takes come from DIR/blocked.jsonl (--store, else $VOICE_ROOT; with no store, only class and race lines).
  import FILE [--source NAME]
      Checks every row whose `spoken` is written (a line of a scope, its Italian unchanged since the export, a
      text the voice can read for each sex it is for, English tags only) and merges them into
      data/voice/spoken.jsonl: {key, sex, it_hash, spoken, reason, provenance}. One bad row and nothing is
      written. --source names who wrote them; by default they are rulings.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from wfj.cmd import voice_make
from wfj.cmd.voice import read_rows as _rows
from wfj.cmd.voice import scope_path, shipped_lines
from wfj.cmd.voice_cast import CONFIG, in_scope, load_config
from wfj.core import casting, voice
from wfj.paths import data_root

CLASS_OR_RACE = "names the player's class or race"


def export_rows(root: Path, cfg: Mapping[str, Any], scope: str, store: Path | None) -> list[dict[str, Any]]:
    """The scope's lines that need a spoken version: those naming the class or race without one in step,
    and the takes the filter still holds blocked (the line, its spoken version and its voice unchanged)."""
    quests, books = voice.read_scope_file(scope_path(root, scope))
    keys = {r["key"] for r in in_scope(_rows(root / "voice" / "speakers.jsonl"), quests, books)}
    lines = shipped_lines(root, quests, books)
    spoken = voice_make.read_spoken(root)
    out: dict[tuple[str, str], dict[str, Any]] = {}

    def row(key: str, sex: str, reason: str) -> dict[str, Any]:
        it = lines[key]
        r: dict[str, Any] = {"key": key, "sex": sex, "it_hash": voice.it_hash(it), "it": it, "spoken": "",
                             "reason": reason}
        old = spoken.get((key, sex))
        if old is not None:
            r["spoken"] = old["spoken"]
            if old.get("it_hash") != r["it_hash"]:
                r["stale"] = True
        return r

    for key in sorted(keys & set(lines)):
        it = lines[key]
        if not voice.needs_spoken(it):
            continue
        sexes = voice.SEXES if voice.needs_variants(it) else ("m",)
        if any(voice_make.spoken_for(spoken, key, s, it)[0] is None for s in sexes):
            out[(key, voice_make.ANY)] = row(key, voice_make.ANY, CLASS_OR_RACE)
    blocked = voice_make.read_blocked(store)
    if blocked:
        held = {t.job.stem: t.fingerprint for t in voice_make.survey(root, cfg, scope).takes}
        for b in blocked.values():
            if held.get(b["file"]) == b["fingerprint"] and (b["key"], b["sex"]) not in out:
                out[(b["key"], b["sex"])] = row(b["key"], b["sex"], f"blocked: {b['reason']}")
    return [out[k] for k in sorted(out)]


def all_lines(root: Path) -> dict[str, str]:
    """{pack key: shipped Italian} over every scope."""
    out: dict[str, str] = {}
    for scope in sorted(voice.SCOPES):
        path = scope_path(root, scope)
        if path.is_file():
            out.update(shipped_lines(root, *voice.read_scope_file(path)))
    return out


def import_rows(
    root: Path, rows: Sequence[Mapping[str, Any]], source: str, today: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """(data/voice/spoken.jsonl rows with the written ones merged in, problems). Rows with no spoken text are
    left out; a row for the same line and sex replaces the old one."""
    lines = all_lines(root)
    written = [r for r in rows if str(r.get("spoken") or "").strip()]
    values = voice_make.line_values(root, lines, written)
    problems: list[str] = []
    new: dict[tuple[str, str], dict[str, Any]] = {}
    for r in written:
        key, sex, text = r.get("key"), r.get("sex"), str(r["spoken"]).strip()
        label = f"{key} ({sex})"
        if key not in lines:
            problems.append(f"{label}: not a line of any scope")
            continue
        if sex not in (*voice.SEXES, voice_make.ANY):
            problems.append(f"{label}: sex must be m, f or {voice_make.ANY}")
            continue
        it = lines[key]
        if r.get("it_hash") != voice.it_hash(it):
            problems.append(f"{label}: the Italian changed since the export; export again")
            continue
        if not isinstance(r.get("reason"), str) or not r["reason"].strip():
            problems.append(f"{label}: a reason is needed (why the line is not said as written)")
            continue
        for s in voice.SEXES if sex == voice_make.ANY else (sex,):
            try:
                said = voice.speech_text(it, key, s, values.get(key, ()), text)
                bad = voice.tag_problem(said)
                if bad:
                    raise voice.VoiceError(f"{key}: {bad}")
            except voice.VoiceError as e:
                problems.append(f"{label}: {e}")
                break
        else:
            new[(key, sex)] = {"key": key, "sex": sex, "it_hash": r["it_hash"], "spoken": text,
                               "reason": r["reason"].strip(),
                               "provenance": {"source": source, "imported": today}}
    merged = {**voice_make.read_spoken(root), **new}
    return [dict(merged[k]) for k in sorted(merged)], problems


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice spoken")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
    e.add_argument("--out", required=True)
    e.add_argument("--store", help="the audio store, for its blocked takes (default: $VOICE_ROOT)")
    e.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
    i = sub.add_parser("import")
    i.add_argument("file")
    i.add_argument("--source", default=casting.MAINTAINER, help="who wrote the spoken versions")
    a = p.parse_args(list(argv))
    root = root or data_root()
    try:
        if a.cmd == "export":
            cfg = load_config(Path(a.config) if a.config else root.parent / CONFIG)
            rows = export_rows(root, cfg, a.scope, voice_make.store_dir(a.store))
            out = Path(a.out)
            voice_make.write_jsonl(out, rows)
            print(f"voice spoken: {len(rows)} line(s) need a spoken version → {out}")
            return 0
        if not Path(a.file).is_file():
            raise FileNotFoundError(f"{a.file}: no such file")
        rows = _rows(Path(a.file))
        merged, problems = import_rows(root, rows, a.source, datetime.date.today().isoformat())
    except (ValueError, KeyError, FileNotFoundError) as err:
        print(f"voice spoken {a.cmd}: {err}", file=sys.stderr)
        return 1
    for pr in problems:
        print(f"voice spoken import: {pr}", file=sys.stderr)
    if problems:
        print(f"voice spoken import: {len(problems)} problem(s), nothing written", file=sys.stderr)
        return 1
    n = sum(1 for r in rows if str(r.get("spoken") or "").strip())
    voice_make.write_jsonl(root / "voice" / voice_make.SPOKEN, merged)
    print(f"voice spoken: {n} spoken version(s) → data/voice/{voice_make.SPOKEN}")
    return 0
