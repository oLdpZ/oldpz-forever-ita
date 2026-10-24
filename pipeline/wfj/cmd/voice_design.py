"""wfj voice design: the designed voices of the roster, made through the engine and written into voice.toml.

  design [--config F] [--env-file F] [--dry-run]
      For every roster voice with a `design` (an English description of the voice) and no `voice` yet, asks
      the engine for a designed voice (`gemini.Engine.create_voice`) and writes its `voice_…` id into
      voice.toml, under the voice's table, one voice at a time (a stop keeps what was made). With --dry-run
      it only lists them. To remake a voice after changing its design, delete its `voice` line and run it
      again: the files made with the old voice are made again (their fingerprint holds the voice).

The API keeps a designed voice a year from its last use, up to 200 per project.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path

from wfj.cmd.voice_cast import CONFIG
from wfj.io import gemini
from wfj.paths import data_root

NAME_PREFIX = "ofi-"


def to_design(text: str) -> list[tuple[str, str]]:
    """(roster id, design) of every roster voice with a design and no voice, in file order."""
    roster = tomllib.loads(text).get("roster", {})
    return [(vid, v["design"]) for vid, v in roster.items() if v.get("design") and v.get("voice") is None]


def with_voice(text: str, vid: str, voice_id: str) -> str:
    """voice.toml's text with `voice = "<id>"` as the first line of the table `[roster.<vid>]`."""
    header = re.compile(rf"^\[roster\.{re.escape(vid)}\][ \t]*$", re.M)
    m = header.search(text)
    if m is None:
        raise ValueError(f"no [roster.{vid}] table")
    return f'{text[: m.end()]}\nvoice = "{voice_id}"{text[m.end():]}'


def design(
    path: Path, create: Callable[[str, str], str], say: Callable[[str], None] = print
) -> tuple[int, dict[str, str]]:
    """Makes the missing designed voices, writing voice.toml after each one: (count made, {roster id: why}
    for each the engine refused, e.g. a description the safety filter blocked; the others are still made)."""
    made, refused = 0, {}
    for vid, description in to_design(path.read_text(encoding="utf-8")):
        try:
            voice_id = create(f"{NAME_PREFIX}{vid}", description)
        except gemini.Busy:
            raise
        except gemini.EngineError as e:
            refused[vid] = str(e)
            continue
        text = path.read_text(encoding="utf-8")
        path.write_bytes(with_voice(text, vid, voice_id).encode("utf-8"))
        say(f"voice design: {vid} → {voice_id}")
        made += 1
    return made, refused


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice design")
    p.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
    p.add_argument("--env-file", help="a .env file holding GEMINI_API_KEY")
    p.add_argument("--dry-run", action="store_true", help="only list the voices to make")
    a = p.parse_args(list(argv))
    root = root or data_root()
    path = Path(a.config) if a.config else root.parent / CONFIG
    try:
        todo = to_design(path.read_text(encoding="utf-8"))
        if a.dry_run or not todo:
            for vid, _ in todo:
                print(f"voice design: {vid} to make")
            print(f"voice design: {len(todo)} voice(s) to make")
            return 0
        engine = gemini.Engine(gemini.read_key(Path(a.env_file) if a.env_file else None))
        made, refused = design(path, engine.create_voice)
    except (ValueError, OSError, tomllib.TOMLDecodeError, gemini.EngineError) as e:
        print(f"voice design: {e}", file=sys.stderr)
        return 1
    print(f"voice design: made {made} voice(s) → {path}")
    for vid, why in refused.items():
        short = " ".join(why.split())[:200]
        print(f"voice design: {vid} refused, change its design: {short}", file=sys.stderr)
    return 1 if refused else 0
