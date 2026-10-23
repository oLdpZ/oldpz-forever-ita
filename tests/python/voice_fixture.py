"""A small world for the voice commands: a VMaNGOS database with the quest, speaker, spawn and book tables,
a data folder with shipped quest, gossip and book lines, forever-vo captures and the client's creature
display tables."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from wfj.core import voice
from wfj.io import client_tables, tables_stamp
from wfj.io.jsonl_store import Store

SRC = {"source": "vmangos@13b49dc", "imported": "2026-10-06"}
HELLO, GREETING, CAPTURED, STRANGER = "Hello, traveller.", "A greeting.", "Captured line.", "Not here."
SIGNED, UNSIGNED, FAR = "a" * 16, "b" * 16, "c" * 16
COLLECTOR = "forever-vo@025070f"
# inside and outside Tirisfal's rectangle on map 0 (x north, y west, z up), and under it (a city below)
IN, OUT, UNDER = (2000.0, 500.0, 40.0), (-9000.0, 100.0, 40.0), (2000.0, 500.0, -60.0)

# each row: entry, name, title, creature type, racial leader flag, gossip menu and first display
CREATURES = [
    (2079, "Undertaker Mordo", "", 7, 0, 7, 1001),
    (1992, "Deathguard Saltain", "", 7, 0, 0, 1002),
    (3597, "Novice Elreth", "", 7, 0, 0, 1001),
    (9000, "Old Bat", "", 1, 1, 0, 1003),
    (6906, "Baelog", "", 7, 0, 0, 1001),
    (5000, "Far Away", "", 7, 0, 0, 1001),
]


def make_speaker_db(path: Path) -> Path:
    """Quests 456 and 457 (Tirisfal) start at 2079; 456 ends at 2079, 457 at 1992; an object starts 458
    (Tirisfal); 460 is another zone's. 2079 has a gossip menu and 1992 a quest window greeting. 2079 and
    1992 stand in Tirisfal, 5000 far south and in the city under it, 9000 on another map; 463 is Deathknell's.
    Sign 800 (pages 15 then 16) stands in Tirisfal, sign 801 (page 20) far south and under it; 802 is a
    chest."""
    db = sqlite3.connect(path)
    for t in ("creature_questrelation", "creature_involvedrelation", "gameobject_questrelation"):
        db.execute(f"CREATE TABLE {t} (id INT, quest INT, patch_min INT, patch_max INT)")
    db.execute("CREATE TABLE quest_template (entry INT, patch INT, ZoneOrSort INT)")
    db.execute(
        "CREATE TABLE creature_template (entry INT, patch INT, name TEXT, subname TEXT, type INT, rank INT,"
        " racial_leader INT, gossip_menu_id INT, display_id1 INT, display_id2 INT, display_id3 INT,"
        " display_id4 INT)"
    )
    db.execute("CREATE TABLE creature (guid INT, id INT, map INT, position_x REAL, position_y REAL, position_z REAL)")
    db.execute("CREATE TABLE gameobject_template (entry INT, patch INT, type INT, data0 INT)")
    db.execute("CREATE TABLE gameobject (guid INT, id INT, map INT, position_x REAL, position_y REAL, position_z REAL)")
    db.execute("CREATE TABLE page_text (entry INT, text TEXT, next_page INT)")
    db.execute("CREATE TABLE gossip_menu (entry INT, text_id INT, script_id INT, condition_id INT)")
    db.execute("CREATE TABLE npc_text (ID INT, " + ", ".join(f"BroadcastTextID{i} INT" for i in range(8)) + ")")
    db.execute("CREATE TABLE broadcast_text (entry INT, male_text TEXT, female_text TEXT)")
    db.execute("CREATE TABLE quest_greeting (entry INT, type INT, content_default TEXT)")
    db.execute("CREATE TABLE creature_display_info_addon (display_id INT, build INT, gender INT)")
    for table, id_, quest in [
        ("creature_questrelation", 2079, 456), ("creature_questrelation", 2079, 457),
        ("creature_involvedrelation", 2079, 456), ("creature_involvedrelation", 1992, 457),
        ("gameobject_questrelation", 900, 458),
    ]:
        db.execute(f"INSERT INTO {table} VALUES (?, ?, 0, 10)", (id_, quest))
    # two patches of 456: the zone of the highest one counts
    db.executemany("INSERT INTO quest_template VALUES (?, ?, ?)",
                   [(456, 0, 12), (456, 1, 85), (457, 0, 85), (458, 0, 85), (460, 0, 12), (463, 0, 154)])
    db.executemany("INSERT INTO creature_template VALUES (?, 0, ?, ?, ?, 0, ?, ?, ?, 0, 0, 0)", CREATURES)
    db.executemany("INSERT INTO creature VALUES (?, ?, ?, ?, ?, ?)", [
        (1, 2079, 0, *IN), (2, 1992, 0, *IN), (3, 5000, 0, *OUT), (4, 9000, 1, *IN), (5, 2079, 0, *OUT),
        (6, 5000, 0, *UNDER),
    ])
    db.executemany("INSERT INTO gameobject_template VALUES (?, 0, ?, ?)", [(800, 9, 15), (801, 9, 20), (802, 3, 15)])
    db.executemany("INSERT INTO gameobject VALUES (?, ?, 0, ?, ?, ?)",
                   [(1, 800, *IN), (2, 801, *OUT), (3, 802, *IN), (4, 801, *UNDER)])
    db.executemany("INSERT INTO page_text VALUES (?, ?, ?)", [(15, "p15", 16), (16, "p16", 0), (20, "p20", 0)])
    db.execute("INSERT INTO gossip_menu VALUES (7, 70, 0, 0)")
    db.execute("INSERT INTO npc_text VALUES (70, 700, 0, 0, 0, 0, 0, 0, 0)")
    db.execute("INSERT INTO broadcast_text VALUES (700, ?, ?)", (HELLO, HELLO))
    db.execute("INSERT INTO quest_greeting VALUES (1992, 0, ?)", (GREETING,))
    db.executemany(
        "INSERT INTO creature_display_info_addon VALUES (?, 0, ?)", [(1001, 0), (1002, 1), (1003, 2)]
    )
    db.commit()
    db.close()
    return path


def make_captures(folder: Path, *entries: dict) -> Path:
    """A forever-vo checkout holding one submission with `entries` (capture events)."""
    (folder / "captures").mkdir(parents=True)
    (folder / "captures" / "a.json").write_text(json.dumps({"origin": "a", "quests": list(entries)}))
    return folder


def make_client(folder: Path) -> Path:
    """Display 1001 is a male Forsaken character model; the client knows no other display."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "CreatureDisplayInfo.csv").write_text("ID,ModelID,ExtendedDisplayInfoID,Gender\n1001,5,10,0\n")
    (folder / "CreatureDisplayInfoExtra.csv").write_text("ID,DisplayRaceID,DisplaySexID\n10,5,0\n")
    (folder / "ChrRaces.csv").write_text("ID,ClientFileString\n5,Scourge\n")
    tables_stamp.write(folder, client_tables.DISPLAY_TABLES, "db2@1.60.1.70450")
    return folder


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _it(id_, field, it, **kw):
    return {"id": id_, "field": field, "it": it, "status": "trusted", **kw}


def _en(id_, field, en, src="vmangos@13b49dc", **kw):
    return {"id": id_, "field": field, "en": en, "src": src, **kw}


def make_data(tmp_path: Path) -> Path:
    """A data folder: quests 456, 457 and 459 (Forever's) ship Italian, 458 has English only; gossip, two
    book pages (one signed by Baelog) and Baelog cast to a voice."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    store, english = Store(data), Store(data, english=True)
    store.save("quest", [
        _it(456, "description", "Salve, {name}. Difendi la valle."),
        _it(456, "completion", "Ben fatto."),
        _it(456, "title", "Titolo"),
        _it(457, "description", "Uccidi $N1 lupi."),
        _it(457, "completion", "Grazie."),
        _it(459, "description", "Prega al santuario."),
    ])
    english.save("quest", [
        _en(457, "description", "Kill 7 wolves."),
        _en(458, "description", "Read the sign."),
        _en(459, "description", "Pray at the shrine.", src="wdb@1.60.1.70450"),
        _en(461, "description", "Go far.", src="wdb@1.60.1.70450"),
        _en(462, "description", "Nobody saw this one.", src="wdb@1.60.1.70450"),
    ])
    store.save("gossip", [
        _it(voice.gossip_id(t), "text", it)
        for t, it in ((HELLO, "Salve, viandante."), (GREETING, "Un saluto."), (CAPTURED, "Ti ho visto."),
                      (STRANGER, "Non qui."))
    ])
    english.save("gossip", [
        _en(voice.gossip_id(HELLO), "text", HELLO, src=COLLECTOR, npcs=[3597]),
        _en(voice.gossip_id(CAPTURED), "text", CAPTURED, src=COLLECTOR, npcs=[1992]),
        _en(voice.gossip_id(STRANGER), "text", STRANGER, src=COLLECTOR, npcs=[5000]),
    ])
    english.save("book", [
        _en(15, "text", "Hello Morgan,$B$B-Baelog", hash=SIGNED),
        _en(16, "text", "No signature here at all.", hash=UNSIGNED),
        _en(20, "text", "A far sign.", hash=FAR),
    ])
    store.save("book", [
        _it(15, "text", "Caro Morgan.", english={"hash": SIGNED}),
        _it(16, "text", "Una pagina senza firma.", english={"hash": UNSIGNED}),
        _it(20, "text", "Un cartello lontano.", english={"hash": FAR}),
    ])
    write_rows(data / "voice" / "voices.jsonl", [
        {"creature": 6906, "voice": "m", "row": "male", "provenance": SRC},
    ])
    return data
