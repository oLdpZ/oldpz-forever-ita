"""Quest objective text as a data type, keyed by QuestObjective id in data/, one row
{ text, h1, status } per id in the generated Lua, found in the addon by the h1 (ADR-031)."""

from pathlib import Path

from wfj.cmd import validate
from wfj.core.hashing import key
from wfj.core.normalize import normalize_v1
from wfj.core.status import Scope, decide
from wfj.dev.translate_batch import objective_names
from wfj.emit import lua_writer, schema
from wfj.io.jsonl_store import Store

MACHINE = {"class": "machine", "model": "m", "source": "draft-objective@2026-09-19",
           "imported": "2026-09-19"}


def _line(id_, it, en, status="trusted"):
    return {"id": id_, "field": "text", "it": it, "status": status, "checks": [], "reasons": [],
            "provenance": dict(MACHINE), "english": {"hash": key(normalize_v1(en)), "src": "wdb@1.60.1.69913"},
            "conflicts": []}


def _names(root: Path) -> dict[int, str]:
    return objective_names(root)  # the one reader `translate_batch cut` uses too


def test_the_row_is_text_h1_status():
    en = "Rescue Drull"
    rows = lua_writer.rows("objective", [_line(380001, "Drullを救出する", en)])
    assert rows == {380001: ['"Drullを救出する"', lua_writer.h1_literal(key(normalize_v1(en))), '"."']}
    assert schema.SLOTS["objective"] == {"fields": ["text"], "hash": 1, "status": 3}
    assert schema.shard_relpath("objective", schema.shard_of(380001)) == "Data/Objective/Objective_0380.lua"


def test_an_objective_is_checked_as_prose():
    """PROSE_KINDS: a number in the Italian must be the English's. A name is no reason (ADR-101): every Italian
    word is Latin."""
    en = "Kill 8 Wolves near Vol'jin"
    scope = Scope(kind="objective", fields={"text": normalize_v1(en)}, hashes={"text": key(normalize_v1(en))},
                  raw={"text": en}, src="wdb@1.60.1.69913")
    ok = decide(_line(1, "Uccidi 8 lupi vicino a Thrall", en, "pending"), scope, set(), key(normalize_v1(en)))
    assert ok.status == "trusted", ok.reasons
    bad = decide(_line(1, "Uccidi 9 lupi vicino a Vol'jin", en, "pending"), scope, set(), key(normalize_v1(en)))
    assert bad.status == "rejected" and bad.reasons == ["numbers_changed:9"]


def test_one_english_ships_one_italian(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    Store(d).save("objective", [_line(1, "Towerに印をつける", "Tower Marked"), _line(2, "Towerを示す", "Tower Marked"),
                                _line(3, "Drullを救出する", "Rescue Drull"), _line(4, "Drullを救出する", "Rescue Drull")])
    assert validate.rule_objective(Store(d)) == [
        "objective ambiguous: objective 1, objective 2 share one English fingerprint with different Italian"
    ]


def test_an_area_line_is_checked_as_prose_against_its_own_english(tmp_path):
    """`check` scopes area (no NOT_IN_SCOPE): a line keyed by the quest id is judged against the
    area English (a number must be the English's, PROSE_KINDS) and records that English as its baseline."""
    from wfj.cmd.check import TYPES, check_type, scopes_for
    from wfj.core.model import english_line

    en = "Escort Corporal Keeshan back to Redridge in 5 minutes"
    eng = Store(tmp_path, english=True)
    eng.save("area", [english_line(219, "text", en, key(normalize_v1(en)), "wdb@1.15.9.69722")])
    assert "area" in TYPES
    scopes = scopes_for(eng, Store(tmp_path), "area")
    ok, bad = (dict(_line(219, it, en, "pending"), english=None) for it in (
        "Scorta il Caporale Keeshan a Redridge in 5 minuti", "Scorta il Caporale Keeshan a Redridge in 6 minuti"))
    assert check_type([ok], scopes, set())[0]["status"] == "trusted"
    assert check_type([ok], scopes, set())[0]["english"] == {"hash": key(normalize_v1(en)),
                                                             "src": "wdb@1.15.9.69722"}
    assert check_type([bad], scopes, set())[0]["status"] == "rejected"
