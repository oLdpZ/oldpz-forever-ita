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
    # a city on the zone's map, inside its rectangle: (x range, y range) each, left out
    cut: tuple[tuple[tuple[float, float], tuple[float, float]], ...] = ()

    def holds(self, map_id: int, x: float, y: float, z: float) -> bool:
        if any(cx[0] <= x <= cx[1] and cy[0] <= y <= cy[1] for cx, cy in self.cut):
            return False
        return (map_id == self.map and self.x[0] <= x <= self.x[1] and self.y[0] <= y <= self.y[1]
                and z >= self.floor)


# The world map's bounds of each zone (WorldMapArea: LocBottom/LocTop are x, LocRight/LocLeft are y; on
# 1.60.1 UiMapAssignment's Region_0/3 are x, Region_1/4 y).
# Tirisfal Glades (area 85; WorldMapArea 20, map 0) and Deathknell (area 154), its starting area, which the
# database files as a zone of its own. Undercity lies under the glades, below sea level.
TIRISFAL = Zone((85, 154), 0, (829.1666, 3837.4999), (-1485.4166, 3033.3333), 0.0)
# On Kalimdor a map rectangle (UiMapAssignment) spans the neighbours too: Durotar's (x -1716..1808,
# y -7250..-1962) holds Ratchet, the Barrens' edge and part of Ashenvale, Mulgore's (x -3835..267,
# y -3675..2479) Camp Taurajo and the Barrens. So these boxes are the zones' land: the spawns of the NPCs of
# their quests (those inside the zone) with a margin, the coast and the river borders.
# Durotar (area 14, map 1) and the Valley of Trials (363), up to the Southfury river (Ratchet and the
# Barrens are west of it). Orgrimmar (UiMap 1454) is cut out.
DUROTAR = Zone((14, 363), 1, (-1400.0, 1400.0), (-5600.0, -3850.0), -1000.0,
               (((1338.4606, 2273.8772), (-5083.2056, -3680.6010)),))
# Mulgore (area 215, map 1), Red Cloud Mesa (220, Camp Narache) and Palemane Rock (221), north of the
# Barrens (Camp Taurajo). Thunder Bluff (UiMap 1456) is cut out.
MULGORE = Zone((215, 220, 221), 1, (-3500.0, -600.0), (-1300.0, 600.0), -1000.0,
               (((-1545.8333, -850.0), (-527.0833, 516.6666)),))
# On the Eastern Kingdoms and Teldrassil too the map rectangles span the neighbours (Elwynn's holds the north
# of Westfall and Duskwood, Dun Morogh's the west of Loch Modan, Teldrassil's the sea down to Darkshore), so
# these boxes are again the zones' land, from the spawns of their quests' NPCs with a margin.
# Elwynn Forest (area 12, map 0) and Northshire (9); Westfall and Duskwood lie south of it. Stormwind
# (UiMap 1453) is cut out.
ELWYNN = Zone((12, 9), 0, (-10050.0, -8550.0), (-1550.0, 950.0), -1000.0,
              (((-9154.1699, -7995.8301), (-14.5840, 1722.9200)),))
# Dun Morogh (area 1, map 0) and Coldridge Valley (132), up to the South Gate (Loch Modan is east of it).
# Ironforge (UiMap 1455) is cut out.
DUN_MOROGH = Zone((1, 132), 0, (-6700.0, -4700.0), (-2650.0, 1300.0), -1000.0,
                  (((-5096.8457, -4569.2412), (-1504.2164, -713.5914)),))
# Teldrassil (area 141, map 1), Shadowglen (188) and Rut'theran Village by the sea; Darkshore is south of it.
# Darnassus (UiMap 1457) is cut out.
TELDRASSIL = Zone((141, 188), 1, (8350.0, 11200.0), (-200.0, 2950.0), -1000.0,
                  (((9532.5869, 10238.3164), (1880.0295, 2938.3628)),))
# A scope is one or more zones: one voice pack holds a scope.
ZONES: dict[str, tuple[Zone, ...]] = {
    "tirisfal": (TIRISFAL,),
    # the Horde's starting zones: the undead, the orcs and trolls, the tauren
    "orda": (TIRISFAL, DUROTAR, MULGORE),
    # the Alliance's starting zones: the humans, the dwarves and gnomes, the night elves
    "alleanza": (ELWYNN, DUN_MOROGH, TELDRASSIL),
    # both: one pack for every starting zone
    "iniziali": (TIRISFAL, DUROTAR, MULGORE, ELWYNN, DUN_MOROGH, TELDRASSIL),
}


# The whole game: every quest with a voiced field and every book page, wherever it stands.
ALL = "tutto"


def everything(
    root: Path, report: dict[str, list[str]]
) -> tuple[tuple[int, ...], tuple[str, ...], dict[str, list[str]]]:
    """(quest ids, book keys, report) of the whole game: the English store's quests that have a voiced field
    and all its book pages. Nothing is placed, so the report stays empty."""
    english = Store(root, english=True).load("quest")
    quests = {int(ln["id"]) for ln in english if ln.get("field") in voice.FIELDS}
    pages = set(book_hashes(root).values())
    return tuple(sorted(quests)), tuple(sorted(pages)), report


def build(
    root: Path, db: Path, scope: str, captures: Path | None
) -> tuple[tuple[int, ...], tuple[str, ...], dict[str, list[str]]]:
    """(quest ids, book keys, report) of a zone scope. Report: `forever` (Forever quests whose giver stands
    inside), `outside` (those whose giver stands elsewhere), `unplaced` (those that could not be placed:
    no giver captured, an object, or a creature the database never spawns) and `pages` (pages with no
    English)."""
    report: dict[str, list[str]] = {"forever": [], "outside": [], "unplaced": [], "pages": []}
    if scope == ALL:
        return everything(root, report)
    parts = ZONES[scope]
    zones = vmangos.read_quest_zones(db)
    quests = {q for q, z in zones.items() if any(z in zone.zones for zone in parts)}
    spawns = vmangos.read_creature_spawns(db)
    inside = {c for c, points in spawns.items() if any(zone.holds(*p) for p in points for zone in parts)}
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
    objects = [(zone, obj) for zone in parts for obj in vmangos.read_text_objects(db, zone.map)]
    for zone, (first, x, y, z) in objects:
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
    head = [f"# The {scope} voice scope: written by `wfj voice scope {scope}`; do not edit."]
    if scope == ALL:
        head.append("# Quests: every quest with a voiced field. `b <key>`: every book page.")
        return "\n".join([*head, *map(str, quests), *(f"b {b}" for b in books)]) + "\n"
    parts = ZONES[scope]
    for zone in parts:
        zones = ", ".join(str(z) for z in zone.zones)
        cut = f", less {len(zone.cut)} city area(s)" if zone.cut else ""
        head += [
            f"# Quests: the database's quests of zones {zones}, and Forever's quests whose",
            f"# captured giver stands on map {zone.map} inside the zone's map bounds{cut},"
            f" above z {zone.floor:g}.",
        ]
    head.append("# `b <key>`: a page of a sign or a book standing there.")
    return "\n".join([*head, *map(str, quests), *(f"b {b}" for b in books)]) + "\n"


def run(argv: Sequence[str]) -> int:
    p = argparse.ArgumentParser(prog="wfj voice scope")
    p.add_argument("scope", choices=sorted([*ZONES, ALL]))
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
