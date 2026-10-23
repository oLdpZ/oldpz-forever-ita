"""wfj voice scope NAME --vmangos FILE [--forever-vo DIR] [--out FILE]: writes a voice scope's list (the
quests and book pages `voice.read_scope_file` reads; default its file under pipeline/), which is committed.

A scope is a zone: its quests are the database's quests of that zone (and of its starting area), and
Forever's own quests (those the database lacks) whose giver, as the players' captures name it, stands inside
the zone's map bounds; its book pages are every page of the signs and books (text objects) standing inside
those bounds. The bounds are a rectangle, so a little of the neighbouring zones falls inside it; a city under
the zone is left out by its depth. What cannot be placed is counted, never guessed: a Forever quest with no
captured giver, one an object gives, or one given by a creature the database never spawns. The class quests
(a quest sort, not a zone) are not in a zone scope.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from wfj.cmd.voice import book_hashes, scope_path
from wfj.core import voice
from wfj.io import forever_vo, vmangos
from wfj.io.jsonl_store import Store
from wfj.paths import data_root


@dataclass(frozen=True)
class Zone:
    zones: tuple[int, ...]  # AreaTable ids, as quest_template.ZoneOrSort names them
    map: int
    x: tuple[float, float]  # south, north
    y: tuple[float, float]  # east, west
    floor: float  # a spawn below it stands in a city under the zone, not in the zone

    def holds(self, map_id: int, x: float, y: float, z: float) -> bool:
        return (map_id == self.map and self.x[0] <= x <= self.x[1] and self.y[0] <= y <= self.y[1]
                and z >= self.floor)


# The world map's bounds of each zone (WorldMapArea: LocBottom/LocTop are x, LocRight/LocLeft are y).
ZONES = {
    # Tirisfal Glades (area 85; WorldMapArea 20, map 0) and Deathknell (area 154), its starting area, which
    # the database files as a zone of its own. Undercity lies under the glades, below sea level.
    "tirisfal": Zone((85, 154), 0, (829.1666, 3837.4999), (-1485.4166, 3033.3333), 0.0),
}


def build(
    root: Path, db: Path, scope: str, captures: Path | None
) -> tuple[tuple[int, ...], tuple[str, ...], dict[str, list[str]]]:
    """(quest ids, book keys, report) of a zone scope. Report: `forever` (Forever quests whose giver stands
    inside), `outside` (those whose giver stands elsewhere), `unplaced` (those that could not be placed:
    no giver captured, an object, or a creature the database never spawns) and `pages` (pages with no
    English)."""
    zone = ZONES[scope]
    report: dict[str, list[str]] = {"forever": [], "outside": [], "unplaced": [], "pages": []}
    zones = vmangos.read_quest_zones(db)
    quests = {q for q, z in zones.items() if z in zone.zones}
    spawns = vmangos.read_creature_spawns(db)
    inside = {c for c, points in spawns.items() if any(zone.holds(*p) for p in points)}
    seen = forever_vo.read_quest_speakers(captures) if captures is not None else {}
    forever = sorted({int(ln["id"]) for ln in Store(root, english=True).load("quest")} - set(zones))
    for q in forever:
        giver = voice.captured_speaker(seen.get((q, "description"), []))
        if giver is None:
            report["unplaced"].append(f"{q}: no giver captured")
        elif not isinstance(giver, int):
            report["unplaced"].append(f"{q}: given by an object")
        elif giver in inside:
            quests.add(q)
            report["forever"].append(f"{q}: given by {giver}")
        elif giver in spawns:
            report["outside"].append(f"{q}: given by {giver}")
        else:
            report["unplaced"].append(f"{q}: given by {giver}, whom the database never spawns")
    hashes, after = book_hashes(root), vmangos.read_next_pages(db)
    pages: set[str] = set()
    for first, x, y, z in vmangos.read_text_objects(db, zone.map):
        if not zone.holds(zone.map, x, y, z):
            continue
        page, walked = first, set()
        while page and page not in walked:  # a chain that loops back ends where it repeats
            walked.add(page)
            if page in hashes:
                pages.add(hashes[page])
            else:
                report["pages"].append(f"page {page}: no English")
            page = after.get(page, 0)
    report["pages"] = sorted(set(report["pages"]))
    return tuple(sorted(quests)), tuple(sorted(pages)), report


def text(scope: str, quests: Sequence[int], books: Sequence[str]) -> str:
    zone = ZONES[scope]
    zones = ", ".join(str(z) for z in zone.zones)
    head = [
        f"# The {scope} voice scope: written by `wfj voice scope {scope}`; do not edit.",
        f"# Quests: the database's quests of zones {zones}, and Forever's quests whose",
        f"# captured giver stands on map {zone.map} inside the zone's map bounds, above z {zone.floor:g}.",
        "# `b <key>`: a page of a sign or a book standing there.",
    ]
    return "\n".join([*head, *map(str, quests), *(f"b {b}" for b in books)]) + "\n"


def run(argv: Sequence[str]) -> int:
    p = argparse.ArgumentParser(prog="wfj voice scope")
    p.add_argument("scope", choices=sorted(ZONES))
    p.add_argument("--vmangos", required=True)
    p.add_argument("--forever-vo", help="forever-vo, pinned: who gives the quests the database lacks")
    p.add_argument("--out", help="default: the scope's file under pipeline/")
    p.add_argument("--list", action="store_true", help="print each Forever quest that could not be placed")
    a = p.parse_args(list(argv))
    root = data_root()
    try:
        captures = Path(a.forever_vo) if a.forever_vo else None
        quests, books, report = build(root, Path(a.vmangos), a.scope, captures)
    except (ValueError, FileNotFoundError, vmangos.VmangosError) as e:
        print(f"voice scope: {e}", file=sys.stderr)
        return 1
    out = Path(a.out) if a.out else scope_path(root, a.scope)
    out.write_text(text(a.scope, quests, books), encoding="utf-8")
    forever = len(report["forever"])
    print(f"voice scope: {len(quests)} quests ({forever} Forever's), {len(books)} book pages → {out}")
    print(f"voice scope: Forever quests given elsewhere: {len(report['outside'])}")
    for why in ("no giver captured", "given by an object", "whom the database never spawns"):
        n = sum(u.endswith(why) for u in report["unplaced"])
        print(f"voice scope: Forever quests not placed, {why}: {n}")
    for item in (report["unplaced"] if a.list else []) + report["pages"]:
        print(f"voice scope: not placed: {item}")
    return 0
