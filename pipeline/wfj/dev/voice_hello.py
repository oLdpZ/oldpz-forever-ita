"""The NPCs' greeting on a click and goodbye: the client's short voice sounds (NPCSounds: greeting,
goodbye and annoyed kits per voice set) have no text, so the addon silences their files and plays short
Italian lines of the NPC's own voice in their place.

    python -m wfj.dev.voice_hello --vmangos <mangos.sqlite> --displays <CreatureDisplayInfo.csv>
        --npc-sounds <NPCSounds.csv> --sound-kits <SoundKitEntry.csv>

Writes data/voice/hello.jsonl (the lines: key `n-<voice>-<slot><k>`, voice, speaker, Italian),
data/voice/greeters.jsonl (creature → the voice that greets) and pipeline/voice_hello_mute.txt (the English
files). The lines come from pipeline/voice_hello.tsv (`race`, `slot` g/b/p, line; race `*` for every race).

An NPC that opens a window (npc_flags) greets with its own voice (data/voice/voices.jsonl); one without
a voice with the voice most NPCs of its voice set have. A set no voiced NPC uses keeps its English files.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wfj.core.hashing import key as hash_key

SLOTS = (("g", 3), ("b", 2), ("p", 2))  # greeting, goodbye, annoyed: how many lines each voice says


@dataclass(frozen=True)
class Plan:
    lines: list[dict[str, Any]]
    greeters: dict[int, str]
    mute: list[int]


def read_phrases(path: Path) -> dict[str, dict[str, list[str]]]:
    out: dict[str, dict[str, list[str]]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        race, slot, line = raw.split("\t")
        out.setdefault(race, {}).setdefault(slot, []).append(line)
    return out


def _pick(
    voice: str, race: str, slot: str, n: int, phrases: Mapping[str, Mapping[str, list[str]]]
) -> list[str]:
    """`n` different lines: the race's own first, then the common ones from a place the voice's id picks."""
    own = list(phrases.get(race, {}).get(slot, []))
    common = [x for x in phrases.get("*", {}).get(slot, []) if x not in own]
    if common:
        at = int(hash_key(f"{voice}|{slot}")[:8], 16) % len(common)
        common = common[at:] + common[:at]
    return (own + common)[:n]


def plan(  # noqa: PLR0913 - the tables are injected for the tests
    greeters: Sequence[tuple[int, int]],
    cast: Mapping[int, str],
    races: Mapping[int, str],
    sets: Mapping[int, tuple[int, ...]],
    kits: Mapping[int, Sequence[int]],
    phrases: Mapping[str, Mapping[str, list[str]]],
) -> Plan:
    by_set: dict[int, Counter[str]] = defaultdict(Counter)
    for c, s in greeters:
        if c in cast:
            by_set[s][cast[c]] += 1
    who: dict[int, str] = {}
    covered: set[int] = set()
    for c, s in greeters:
        v = cast.get(c)
        if v is None and by_set[s]:
            v = min(by_set[s].items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if v is not None:
            who[c] = v
            covered.add(s)
    mute = sorted({f for s in covered for k in sets.get(s, ()) if k for f in kits.get(k, ())})
    lines: list[dict[str, Any]] = []
    for v in sorted(set(who.values())):
        own = sorted(c for c, x in cast.items() if x == v and c in who)
        speaker = own[0] if own else min(c for c, x in who.items() if x == v)
        race_votes = Counter(races[c] for c, x in who.items() if x == v and c in races)
        race = min(race_votes.items(), key=lambda kv: (-kv[1], kv[0]))[0] if race_votes else "*"
        for slot, n in SLOTS:
            for k, it in enumerate(_pick(v, race, slot, n, phrases), 1):
                lines.append({"key": f"n-{v}-{slot}{k}", "voice": v, "speaker": speaker, "it": it})
    return Plan(lines, dict(sorted(who.items())), mute)


def _csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m wfj.dev.voice_hello")
    p.add_argument("--vmangos", required=True)
    p.add_argument("--displays", required=True)
    p.add_argument("--npc-sounds", required=True)
    p.add_argument("--sound-kits", required=True)
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    a = p.parse_args(argv)
    root = Path(a.root)
    db = sqlite3.connect(a.vmangos)
    rows = db.execute(
        "SELECT t.entry, t.npc_flags, t.display_id1 FROM creature_template t"
        " JOIN (SELECT entry, MAX(patch) AS patch FROM creature_template GROUP BY entry) m"
        " ON t.entry = m.entry AND t.patch = m.patch"
    ).fetchall()
    sound_of = {int(r["ID"]): int(r["NPCSoundID"] or 0) for r in _csv(Path(a.displays))}
    greeters = [(e, sound_of[d]) for e, flags, d in rows if flags and sound_of.get(d)]
    sets = {int(r["ID"]): tuple(int(r[f"SoundID_{i}"]) for i in range(3)) for r in _csv(Path(a.npc_sounds))}
    kits: dict[int, list[int]] = defaultdict(list)
    for r in _csv(Path(a.sound_kits)):
        kits[int(r["SoundKitID"])].append(int(r["FileDataID"]))
    cast = {int(r["creature"]): r["voice"] for r in _jsonl(root / "data/voice/voices.jsonl")}
    profiles = _jsonl(root / "data/voice/profiles.jsonl")
    races = {int(r["creature"]): r["race"] for r in profiles if r.get("race")}
    result = plan(greeters, cast, races, sets, kits, read_phrases(root / "pipeline/voice_hello.tsv"))
    (root / "data/voice/hello.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result.lines), encoding="utf-8")
    (root / "data/voice/greeters.jsonl").write_text(
        "".join(json.dumps({"creature": c, "voice": v}) + "\n" for c, v in result.greeters.items()),
        encoding="utf-8")
    (root / "pipeline/voice_hello_mute.txt").write_text(
        "# the client's English greeting / goodbye / annoyed files the addon silences (wfj.dev.voice_hello)\n"
        + "".join(f"{f}\n" for f in result.mute), encoding="utf-8")
    print(f"voice hello: {len(result.greeters)} NPCs greet · {len(set(result.greeters.values()))} voices ·"
          f" {len(result.lines)} lines · {len(result.mute)} English files silenced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
