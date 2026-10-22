"""`wfj.dev.gossip_priority`: which dialogue lines a level 1-20 player meets first."""

import sqlite3
from pathlib import Path

import pytest

from wfj.core.hashing import key
from wfj.core.model import english_line
from wfj.core.normalize import normalize_v1
from wfj.dev import gossip_priority
from wfj.io import vmangos
from wfj.io.jsonl_store import Store

SHARED = "Shared by two."
TEXTS = {1: "Hail, traveller.", 2: "Hello, friend.", 3: "Begone, $C."}
MISSING = "Newer than the store."
YELL = "Look out!"
OPTION = "Train me."

SCHEMA = [
    "creature_questrelation (id, quest)",
    "creature_involvedrelation (id, quest)",
    "gameobject_questrelation (id, quest)",
    "creature_template (entry, patch, gossip_menu_id, display_id1, level_max)",
    "gossip_menu (entry, text_id)",
    "npc_text (ID, " + ", ".join(f"BroadcastTextID{i}" for i in range(8)) + ")",
    "broadcast_text (entry, male_text, female_text)",
    "quest_greeting (entry, type, content_default)",
    "creature_display_info_addon (display_id, build, gender)",
    "gossip_menu_option (option_text)",
]


def _h(en: str) -> str:
    return key(normalize_v1(en))


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "mangos.sqlite"
    db = sqlite3.connect(path)
    for s in SCHEMA:
        db.execute(f"CREATE TABLE {s}")
    # PNG 1 gives quest 10, PNG 2 gives quest 20; PNG 3 gives none. Menu n belongs to PNG n.
    db.executemany("INSERT INTO creature_questrelation VALUES (?, ?)", [(1, 10), (2, 20)])
    db.executemany("INSERT INTO creature_template VALUES (?, 0, ?, 0, ?)", [(1, 1, 12), (2, 2, 25), (3, 3, 60)])
    # an older patch row with a low level must not win over the highest patch
    db.execute("INSERT INTO creature_template VALUES (3, -1, 3, 0, 5)")
    db.executemany("INSERT INTO gossip_menu VALUES (?, ?)", [(1, 1), (2, 2), (3, 3)])
    db.executemany("INSERT INTO npc_text (ID, BroadcastTextID0, BroadcastTextID1) VALUES (?, ?, ?)",
                   [(1, 1, 4), (2, 2, 0), (3, 3, 4), ])
    db.execute("INSERT INTO npc_text (ID, BroadcastTextID0) VALUES (5, 5)")
    db.executemany("INSERT INTO broadcast_text VALUES (?, ?, '')", [
        (1, TEXTS[1]), (2, TEXTS[2]), (3, TEXTS[3]), (4, SHARED), (5, MISSING), (6, YELL)])
    db.execute("INSERT INTO gossip_menu VALUES (3, 5)")  # PNG 3 also says a line the store lacks
    db.execute("INSERT INTO gossip_menu_option VALUES (?)", (OPTION,))
    db.commit()
    db.close()
    return path


@pytest.fixture
def world(tmp_path: Path):
    data = tmp_path / "data"
    store = [TEXTS[1], TEXTS[2], TEXTS[3], SHARED, YELL, OPTION, "Someone sneezes.", ]
    Store(data, english=True).save(
        "gossip", [english_line(_h(en), "text", en, _h(en), "vmangos@13b49dc") for en in store]
    )
    levels = tmp_path / "quest_levels.tsv"
    levels.write_text("id\tmin\tlvl\tfonte\n10\t1\t5\tx\n20\t30\t40\tx\n30\t\t\tassente\n", encoding="utf-8")
    return _db(tmp_path), data, levels


def _tiers(world) -> dict[str, int]:
    db, data, levels = world
    return dict(gossip_priority.build(db, data, levels))


def test_quest_givers_up_to_20_and_options_are_tier_1(world):
    t = _tiers(world)
    assert t[_h(TEXTS[1])] == 1
    assert t[_h(OPTION)] == 1


def test_low_level_npcs_are_tier_2(world):
    assert _tiers(world)[_h(TEXTS[2])] == 2


def test_other_npcs_are_tier_3(world):
    assert _tiers(world)[_h(TEXTS[3])] == 3


def test_lines_of_no_npc_are_tier_4(world):
    t = _tiers(world)
    assert t[_h(YELL)] == 4 and t[_h("Someone sneezes.")] == 4


def test_a_line_keeps_its_lowest_tier(world):
    assert _tiers(world)[_h(SHARED)] == 1  # said by PNG 1 (tier 1) and PNG 3 (tier 3)


def test_hashes_missing_from_the_store_are_dropped_and_counted(world):
    db, data, levels = world
    rows, dropped = gossip_priority.classify(db, data, levels)
    assert _h(MISSING) not in dict(rows)
    assert dropped == 1
    assert rows == sorted(rows, key=lambda r: (r[1], r[0]))


def test_reads_highest_patch_level_and_distinct_options(world):
    db = world[0]
    assert vmangos.read_creature_max_levels(db) == {1: 12, 2: 25, 3: 60}
    assert vmangos.read_gossip_options(db) == [OPTION]
