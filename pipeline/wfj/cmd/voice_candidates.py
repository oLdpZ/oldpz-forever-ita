"""wfj voice candidates [--min N] [--config F]: the creatures that earn a designed voice of their own.

The owner's casting rule: a creature with N or more lines in all (quest fields, greetings `g-`, lines in
chat `s-`; as the main speaker or one of the `others`) gets a voice designed for it; the others keep a stock
voice of their race and sex. Lists, from data/voice/speakers.jsonl and voices.jsonl, every such creature
whose voice is not designed yet (a roster voice with no `design` in voice.toml): its id, English name and
lines by kind, most lines first. Writes nothing: the designs are written into voice.toml by hand, then
`wfj voice design` makes them.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wfj.cmd.voice import read_rows
from wfj.cmd.voice_cast import CONFIG
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

MINIMUM = 8  # the owner's bar (2026-10-26)


@dataclass(frozen=True)
class Candidate:
    creature: int
    quest: int
    greeting: int
    chat: int

    @property
    def lines(self) -> int:
        return self.quest + self.greeting + self.chat


def candidates(
    rows: Sequence[Mapping[str, Any]], voices: Sequence[Mapping[str, Any]], designed: set[str],
    minimum: int,
) -> list[Candidate]:
    """The creatures with `minimum` or more lines whose cast voice (either, for a creature shown as both
    sexes) is not a designed one, most lines first, then by id."""
    counts: dict[int, list[int]] = {}
    for r in rows:
        kind = 1 if r["key"].startswith("g-") else 2 if r["key"].startswith("s-") else 0
        if r["key"].startswith(("b-", "i-")):
            continue
        for c in (r["speaker"], *r.get("others", ())):
            if isinstance(c, int):
                counts.setdefault(c, [0, 0, 0])[kind] += 1
    has_own = {int(v["creature"]) for v in voices
               if v.get("voice") in designed or v.get("female") in designed}
    out = [Candidate(c, *n) for c, n in counts.items() if sum(n) >= minimum and c not in has_own]
    return sorted(out, key=lambda x: (-x.lines, x.creature))


def designed_voices(config: Path) -> set[str]:
    with config.open("rb") as f:
        roster = tomllib.load(f).get("roster", {})
    return {vid for vid, v in roster.items() if "design" in v}


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice candidates")
    p.add_argument("--min", type=int, default=MINIMUM, help="lines a creature needs for a voice of its own")
    p.add_argument("--config", default=None, help="voice.toml (default pipeline/voice.toml)")
    a = p.parse_args(list(argv))
    root = root or data_root()
    config = Path(a.config) if a.config else root.parent / CONFIG
    try:
        designed = designed_voices(config)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"voice candidates: {e}", file=sys.stderr)
        return 1
    rows = read_rows(root / "voice" / "speakers.jsonl")
    found = candidates(rows, read_rows(root / "voice" / "voices.jsonl"), designed, a.min)
    units = Store(root, english=True).load("unit")
    names = {int(r["id"]): r["en"] for r in units if r.get("field") == "name"}
    for c in found:
        print(f"{c.creature}\t{names.get(c.creature, '?')}\t{c.lines}\tquest {c.quest}\tgreeting {c.greeting}"
              f"\tchat {c.chat}")
    print(f"voice candidates: {len(found)} creatures with {a.min}+ lines and no designed voice")
    return 0
