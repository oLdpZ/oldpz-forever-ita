"""Inglese dei PNG (unit.name, unit.subname) da creature_template di VMaNGOS."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from wfj.core.hashing import key
from wfj.core.model import english_line, validate_line
from wfj.core.normalize import normalize_for
from wfj.dev import unit_english
from wfj.io import vmangos
from wfj.io.jsonl_store import Store

SRC = "vmangos@4641790"


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "mangos.sqlite"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE creature_template (entry, patch, name, subname, type, rank, racial_leader,"
        " display_id1, display_id2, display_id3, display_id4)"
    )
    rows = [
        (12696, 0, "Senani Thunderheart", None),
        (3, 0, "Flesh Eater", ""),
        (2, 0, "Defias Thug", "Weapon Merchant"),
        (9, 0, "", "Orphan Title"),  # senza nome: saltato
        (2, -1, "Old Thug", "Old Title"),  # patch piu' bassa: non vince
    ]
    db.executemany("INSERT INTO creature_template VALUES (?, ?, ?, ?, 7, 0, 0, 0, 0, 0, 0)", rows)
    db.commit()
    db.close()
    return path


def _h(en: str) -> str:
    return key(normalize_for("unit", en))


def test_unit_english_rows_from_creature_template(tmp_path):
    rows = unit_english.build(vmangos.read_creatures(_db(tmp_path)), [])
    got = {(r["id"], r["field"]): r["en"] for r in rows}
    assert got == {
        (2, "name"): "Defias Thug",
        (2, "subname"): "Weapon Merchant",
        (3, "name"): "Flesh Eater",
        (12696, "name"): "Senani Thunderheart",
    }
    for r in rows:
        assert r["src"] == SRC
        assert r["hash"] == _h(r["en"])
        assert validate_line("unit", r, english=True) == []


def test_collector_line_wins(tmp_path):
    mine = english_line(3, "name", "Flesh Eater (seen)", _h("Flesh Eater (seen)"), "collector@1.60.1.70205")
    rows = unit_english.build(vmangos.read_creatures(_db(tmp_path)), [mine])
    new_for_3 = [r for r in rows if r["id"] == 3 and r["field"] == "name"]
    assert new_for_3 == []
    assert any(r["id"] == 2 for r in rows)


def test_main_writes_and_keeps_collector(tmp_path):
    root = tmp_path / "data"
    store = Store(root, english=True)
    store.save("unit", [english_line(3, "name", "Flesh Eater", _h("Flesh Eater"), "collector@1.60.1.70205")])
    db = _db(tmp_path)
    assert unit_english.main(["--db", str(db), "--data", str(root)]) == 0
    lines = Store(root, english=True).load("unit")
    assert [(r["id"], r["field"]) for r in lines] == [(2, "name"), (2, "subname"), (3, "name"), (12696, "name")]
    assert [r["src"] for r in lines if r["id"] == 3] == ["collector@1.60.1.70205"]
    # idempotente
    assert unit_english.main(["--db", str(db), "--data", str(root)]) == 0
    assert Store(root, english=True).load("unit") == lines
