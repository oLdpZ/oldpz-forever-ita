"""wfj voice design: the designed voices of the roster, made through the engine and written into voice.toml.

  design [--config F] [--env-file F] [--project N] [--dry-run]
      For every roster voice with a `design` (an English description of the voice) and no `voice` yet, asks
      the engine for a designed voice (`gemini.Engine.create_voice`) and writes its `voice_…` id into
      voice.toml, under the voice's table, one voice at a time (a stop keeps what was made). With --dry-run
      it only lists them. To remake a voice after changing its design, delete its `voice` line and run it
      again: the files made with the old voice are made again (their fingerprint holds the voice).

A project keeps at most 200 designed voices (each for a year from its last use). The run starts in project 1
(GEMINI_API_KEY), or in project N with --project N; when the engine says the project is full it goes on in the
next one (GEMINI_API_KEY_2, _3, …, from the environment or --env-file) and writes `project = N` under each
voice made there, since only that project's key can use it. With no key for a next project it stops, keeping
what was made. A voice the engine keeps failing on (HTTP 500) is left for the next run and listed; three in
a row stop the run (the service is down). A busy engine (the daily quota) stops it too.
"""

from __future__ import annotations

import argparse
import functools
import re
import sys
import time
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path

from wfj.cmd.voice_cast import CONFIG
from wfj.io import gemini
from wfj.paths import data_root

NAME_PREFIX = "ofi-"
WAITS = (5, 15, 45)
DOWN = 3  # voices in a row the engine fails on (HTTP 500) before the run stops: the service is down
_PROJECT_LINE = re.compile(r"^project[ \t]*=.*\n?", re.M)


def to_design(text: str) -> list[tuple[str, str]]:
    """(roster id, design) of every roster voice with a design and no voice, in file order."""
    roster = tomllib.loads(text).get("roster", {})
    return [(vid, v["design"]) for vid, v in roster.items() if v.get("design") and v.get("voice") is None]


def with_voice(text: str, vid: str, voice_id: str, project: int = 1) -> str:
    """voice.toml's text with `voice = "<id>"` as the first line of the table `[roster.<vid>]`, followed by
    `project = <n>` when the voice was made in a project after the first (a `project` line the table held
    from an earlier voice is taken out)."""
    header = re.compile(rf"^\[roster\.{re.escape(vid)}\][ \t]*$", re.M)
    m = header.search(text)
    if m is None:
        raise ValueError(f"no [roster.{vid}] table")
    nxt = re.compile(r"^\[", re.M).search(text, m.end())
    end = nxt.start() if nxt else len(text)
    body = _PROJECT_LINE.sub("", text[m.end():end])
    lines = f'\nvoice = "{voice_id}"' + (f"\nproject = {project}" if project > 1 else "")
    return f"{text[: m.end()]}{lines}{body}{text[end:]}"


def _patiently(call: Callable[[], str], sleep: Callable[[float], None]) -> str:
    """`call`, asked again after 5, 15 and 45 seconds while the engine is busy or failed inside. A full
    project is not asked again: waiting does not empty it."""
    for wait in WAITS:
        try:
            return call()
        except gemini.Busy as e:
            if gemini.voices_full(e):
                raise
            sleep(wait)
    return call()


def _failed_inside(e: gemini.Busy) -> bool:
    return str(e).startswith("HTTP 500")


def design(  # noqa: PLR0913 - the engine, its keys, log and sleep are injected for the tests
    path: Path,
    create: Callable[[int, str, str], str],
    say: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    project: int = 1,
    has_key: Callable[[int], bool] = lambda _n: False,
) -> tuple[int, dict[str, str], str | None]:
    """Makes the missing designed voices, writing voice.toml after each one. `create(project, name,
    description)` makes one in a project; `has_key(n)` says whether project n can be used, for when one is
    full. → (count made, {roster id: why} for each the engine refused, e.g. a description the safety filter
    blocked, or kept failing on; the others are still made; why the run stopped early, or None)."""
    made, refused, failing = 0, {}, 0
    for vid, description in to_design(path.read_text(encoding="utf-8")):
        while True:
            try:
                call = functools.partial(create, project, f"{NAME_PREFIX}{vid}", description)
                voice_id = _patiently(call, sleep)
                break
            except gemini.Busy as e:
                if gemini.voices_full(e):
                    if not has_key(project + 1):
                        return made, refused, (
                            f"project {project} is full and there is no {gemini.key_var(project + 1)} for "
                            "another: add the key of a new project and run it again")
                    say(f"voice design: project {project} is full, going on in project {project + 1}")
                    project += 1
                    continue
                if not _failed_inside(e):
                    raise
                refused[vid] = str(e)
                failing += 1
                if failing >= DOWN:
                    return made, refused, f"the engine failed on {DOWN} voices in a row: run it again later"
                voice_id = None
                break
            except gemini.EngineError as e:
                refused[vid] = str(e)
                voice_id = None
                break
        if voice_id is None:
            continue
        failing = 0
        text = path.read_text(encoding="utf-8")
        path.write_bytes(with_voice(text, vid, voice_id, project).encode("utf-8"))
        where = f" (project {project})" if project > 1 else ""
        say(f"voice design: {vid} → {voice_id}{where}")
        made += 1
    return made, refused, None


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice design")
    p.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
    p.add_argument("--env-file", help="a .env file holding GEMINI_API_KEY (and GEMINI_API_KEY_2, … for the "
                                      "projects after the first)")
    p.add_argument("--project", type=int, default=1, help="the project to start in (default: %(default)s)")
    p.add_argument("--dry-run", action="store_true", help="only list the voices to make")
    a = p.parse_args(list(argv))
    if a.project < 1:
        p.error("--project must be at least 1")
    root = root or data_root()
    path = Path(a.config) if a.config else root.parent / CONFIG
    try:
        todo = to_design(path.read_text(encoding="utf-8"))
        if a.dry_run or not todo:
            for vid, _ in todo:
                print(f"voice design: {vid} to make")
            print(f"voice design: {len(todo)} voice(s) to make")
            return 0
        projects = gemini.Projects(env_file=Path(a.env_file) if a.env_file else None)
        projects.engine(a.project)  # the first project's key, read before anything is asked

        def create(project: int, name: str, description: str) -> str:
            return projects.engine(project).create_voice(name, description)

        made, refused, stopped = design(path, create, project=a.project, has_key=projects.has_key)
    except (ValueError, OSError, tomllib.TOMLDecodeError, gemini.EngineError) as e:
        print(f"voice design: {e}", file=sys.stderr)
        return 1
    print(f"voice design: made {made} voice(s) → {path}")
    for vid, why in refused.items():
        short = " ".join(why.split())[:200]
        if why.startswith("HTTP 500"):
            print(f"voice design: {vid} not made, the engine failed (run it again): {short}", file=sys.stderr)
        else:
            print(f"voice design: {vid} refused, change its design: {short}", file=sys.stderr)
    if stopped:
        print(f"voice design: stopped: {stopped}", file=sys.stderr)
    return 1 if refused or stopped else 0
