"""VMaNGOS core sources (`vmangos/core` at the database's commit) → which creature says a broadcast text.

The boss and event scripts are C++ (`src/scripts/**/*.cpp`): a file names its lines in enums
(`SAY_AGGRO = 11111,`) and registers its scripts (`newscript->Name = "boss_x";`); the database ties a script
name to creatures (`creature_template.script_name`). A file with one script gives every line constant to that
script's creatures. In a file with several, a constant goes to the script whose AI struct uses it
(`GetAI_<script>` → `new <Struct>`, that struct's body); a constant no struct uses, or two use, is reported
and left out. The sources are only read, never built or run.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

_CONSTANT = re.compile(r"\b((?:SAY|YELL|WHISPER|EMOTE)_\w+)\s*=\s*(\d+)")
_NAME = re.compile(r"->\s*Name\s*=\s*\"(\w+)\"")
_GET_AI = re.compile(r"GetAI_(\w+)\s*\([^)]*\)\s*\{[^}]*?new\s+(\w+)")
_STRUCT = re.compile(r"\b(?:struct|class)\s+(\w+)\s*(?::[^{;]*)?\{")


def _bodies(text: str) -> dict[str, str]:
    """Struct name → its body, braces matched."""
    out: dict[str, str] = {}
    for m in _STRUCT.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out[m.group(1)] = text[m.end():i]
    return out


def _file_speech(text: str, where: str, report: list[str]) -> dict[str, list[int]]:
    """Script name → the broadcast ids its creatures say, for one file."""
    constants = {name: int(v) for name, v in _CONSTANT.findall(text)}
    scripts = list(dict.fromkeys(_NAME.findall(text)))
    if not constants or not scripts:
        return {}
    if len(scripts) == 1:
        return {scripts[0]: sorted(set(constants.values()))}
    bodies = _bodies(text)
    struct_of = dict(_GET_AI.findall(text))
    out: dict[str, list[int]] = {s: [] for s in scripts}
    for name, value in constants.items():
        users = [s for s in scripts if re.search(rf"\b{name}\b", bodies.get(struct_of.get(s, ""), ""))]
        if len(users) == 1:
            out[users[0]].append(value)
        elif users:
            report.append(f"{where}: {name} ({value}) used by two scripts {users}: left out")
        else:
            report.append(f"{where}: {name} ({value}) used by no script's AI: left out")
    return {s: sorted(set(v)) for s, v in out.items() if v}


def read_script_speech(
    src: Path, names: Mapping[str, Sequence[int]]
) -> tuple[list[tuple[int, int]], list[str]]:
    """((creature id, broadcast id) pairs, report) from the C++ scripts under `src`/src/scripts. A script no
    creature runs is reported."""
    pairs: set[tuple[int, int]] = set()
    report: list[str] = []
    for path in sorted((src / "src" / "scripts").rglob("*.cpp")):
        where = path.relative_to(src).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for script, ids in _file_speech(text, where, report).items():
            creatures = names.get(script, ())
            if not creatures:
                report.append(f"{where}: script {script} runs on no creature: its lines left out")
            pairs |= {(int(c), i) for c in creatures for i in ids}
    return sorted(pairs), report
