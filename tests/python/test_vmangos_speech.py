"""Who says an NPC's line in chat: the VMaNGOS script tables (wfj.io.vmangos) and the core's C++ boss scripts
(wfj.io.vmangos_src)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from wfj.io import vmangos, vmangos_src

SCRIPT_COLUMNS = ("id INT, delay INT, command INT, datalong INT, target_type INT, dataint INT, dataint2 INT,"
                  " dataint3 INT, dataint4 INT")
SCRIPT_TABLES = ("creature_ai_scripts", "creature_movement_scripts", "quest_start_scripts", "quest_end_scripts",
                 "gossip_scripts", "generic_scripts")


def make_db(path: Path) -> Path:
    """Broadcast texts 1..9; one script per way a line reaches a creature, plus the ones that must not count."""
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE broadcast_text (entry INT, male_text TEXT, female_text TEXT, chat_type INT,"
               " sound_id INT)")
    db.executemany("INSERT INTO broadcast_text VALUES (?, ?, ?, ?, ?)", [
        (1, "AI says", "", 0, 0), (2, "Walker yells", "", 1, 0), (3, "Template walker", "", 0, 0),
        (4, "Quest start", "", 0, 0), (5, "Quest end", "", 0, 0), (6, "Gossip option", "Gossip option (f)", 0, 0),
        (7, "%s growls.", "", 2, 0), (8, "Said by the target", "", 0, 0), (9, "Only a generic script", "", 0, 0),
        (10, "Whisper", "", 4, 77),
    ])
    for t in SCRIPT_TABLES:
        db.execute(f"CREATE TABLE {t} ({SCRIPT_COLUMNS})")
    rows = {
        "creature_ai_scripts": [(100, 0, 0, 0, 0, 1, 0, 0, 0), (101, 0, 0, 0, 0, 0, 0, 0, 7),
                                (102, 0, 0, 0, 1, 8, 0, 0, 0), (103, 0, 15, 0, 0, 1, 0, 0, 0),
                                (104, 0, 0, 0, 0, 10, 0, 0, 0)],
        "creature_movement_scripts": [(200, 0, 0, 0, 0, 2, 0, 0, 0), (201, 0, 0, 0, 0, 0, 3, 0, 0)],
        "quest_start_scripts": [(456, 0, 0, 0, 0, 4, 0, 0, 0)],
        "quest_end_scripts": [(457, 0, 0, 0, 0, 5, 0, 0, 0)],
        "gossip_scripts": [(300, 0, 0, 0, 0, 6, 0, 0, 0)],
        "generic_scripts": [(400, 0, 0, 0, 0, 9, 0, 0, 0)],
    }
    for t, rs in rows.items():
        db.executemany(f"INSERT INTO {t} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rs)
    db.execute("CREATE TABLE creature_ai_events (id INT, creature_id INT, action1_script INT, action2_script INT,"
               " action3_script INT)")
    db.executemany("INSERT INTO creature_ai_events VALUES (?, ?, ?, ?, ?)",
                   [(1, 10, 100, 101, 0), (2, 11, 0, 0, 102), (3, 12, 103, 0, 0), (4, 13, 104, 0, 0)])
    db.execute("CREATE TABLE creature (guid INT, id INT)")
    db.execute("INSERT INTO creature VALUES (5, 20)")
    db.execute("CREATE TABLE creature_movement (id INT, point INT, script_id INT)")
    db.execute("INSERT INTO creature_movement VALUES (5, 1, 200)")
    db.execute("CREATE TABLE creature_movement_template (entry INT, point INT, script_id INT)")
    db.execute("INSERT INTO creature_movement_template VALUES (21, 1, 201)")
    db.execute("CREATE TABLE creature_questrelation (id INT, quest INT)")
    db.execute("INSERT INTO creature_questrelation VALUES (30, 456)")
    db.execute("CREATE TABLE creature_involvedrelation (id INT, quest INT)")
    db.execute("INSERT INTO creature_involvedrelation VALUES (31, 457)")
    db.execute("CREATE TABLE gossip_menu_option (menu_id INT, action_script_id INT)")
    db.execute("INSERT INTO gossip_menu_option VALUES (9, 300)")
    db.execute("CREATE TABLE creature_template (entry INT, patch INT, gossip_menu_id INT, script_name TEXT)")
    db.executemany("INSERT INTO creature_template VALUES (?, ?, ?, ?)",
                   [(40, 0, 9, ""), (40, 1, 9, ""), (50, 0, 0, "boss_one"), (51, 0, 0, "boss_one"),
                    (52, 0, 0, "npc_two")])
    db.commit()
    db.close()
    return path


@pytest.fixture
def db(tmp_path) -> Path:
    return make_db(tmp_path / "mangos.sqlite")


def test_every_script_table_names_the_creature_that_speaks(db):
    got = vmangos.read_speech_speakers(db)
    assert (10, "AI says") in got  # creature_ai_events → creature_ai_scripts
    assert (20, "Walker yells") in got  # creature_movement (a spawn's guid) → creature.id
    assert (21, "Template walker") in got  # creature_movement_template.entry, any dataint slot
    assert (30, "Quest start") in got and (31, "Quest end") in got  # quest giver / ender
    assert (40, "Gossip option") in got and (40, "Gossip option (f)") in got  # both wordings
    assert (13, "Whisper") in got


def test_emotes_other_targets_other_commands_and_unowned_scripts_do_not_count(db):
    got = vmangos.read_speech_speakers(db)
    texts = {t for _, t in got}
    assert "%s growls." not in texts  # an emote is not voiced
    assert "Said by the target" not in texts  # target_type 1: someone else speaks
    assert not any(c == 12 for c, _ in got)  # command 15 is a spell cast, not talk
    assert "Only a generic script" not in texts  # no creature owns a generic script
    assert got == sorted(set(got))  # sorted, distinct (two patches of creature 40 count once)


def test_script_names_and_broadcast_texts(db):
    assert vmangos.read_script_names(db) == {"boss_one": [50, 51], "npc_two": [52]}
    assert vmangos.read_broadcast_texts(db, {1, 6, 7, 99}) == {
        1: ("AI says",), 6: ("Gossip option", "Gossip option (f)")}  # emotes and unknown ids left out
    assert vmangos.read_speech_sounds(db) == {"Whisper": 77}


ONE = """
enum
{
    SAY_AGGRO   = 1,
    YELL_DEATH  = 2,   // a comment
    EMOTE_RAGE  = 7,
    SPELL_FIRE  = 999,
};
struct boss_oneAI : public ScriptedAI {};
void AddSC_boss_one()
{
    Script* newscript = new Script;
    newscript->Name = "boss_one";
    newscript->RegisterSelf();
}
"""
TWO = """
enum { SAY_A = 3, SAY_B = 4, SAY_SHARED = 5, SAY_UNUSED = 6 };
struct npc_twoAI : public ScriptedAI
{
    void Aggro() { DoScriptText(SAY_A, m_creature); DoBroadcastText(SAY_SHARED, m_creature); }
};
struct npc_threeAI : public ScriptedAI
{
    void Aggro() { DoScriptText(SAY_B, m_creature); m_creature->MonsterSay(SAY_SHARED); }
};
CreatureAI* GetAI_npc_two(Creature* c) { return new npc_twoAI(c); }
CreatureAI* GetAI_npc_three(Creature* c) { return new npc_threeAI(c); }
void AddSC_two()
{
    Script* newscript;
    newscript = new Script; newscript->Name = "npc_two"; newscript->GetAI = &GetAI_npc_two; newscript->RegisterSelf();
    newscript = new Script; newscript->Name = "npc_three"; newscript->GetAI = &GetAI_npc_three;
    newscript->RegisterSelf();
}
"""


@pytest.fixture
def src(tmp_path) -> Path:
    root = tmp_path / "core"
    (root / "src" / "scripts" / "zone").mkdir(parents=True)
    (root / "src" / "scripts" / "zone" / "boss_one.cpp").write_text(ONE)
    (root / "src" / "scripts" / "zone" / "two.cpp").write_text(TWO)
    return root


def test_a_file_with_one_script_gives_its_constants_to_that_script_s_creatures(src):
    pairs, _ = vmangos_src.read_script_speech(src, {"boss_one": [50, 51]})
    assert sorted(pairs) == [(50, 1), (50, 2), (50, 7), (51, 1), (51, 2), (51, 7)]  # never SPELL_


def test_in_a_file_with_several_scripts_a_constant_goes_to_the_struct_that_uses_it(src):
    pairs, report = vmangos_src.read_script_speech(src, {"npc_two": [52], "npc_three": [53]})
    assert sorted(pairs) == [(52, 3), (53, 4)]
    assert any("SAY_SHARED" in r and "two scripts" in r for r in report)
    assert any("SAY_UNUSED" in r and "no script" in r for r in report)


def test_a_script_no_creature_uses_is_reported_not_guessed(src):
    pairs, report = vmangos_src.read_script_speech(src, {})
    assert pairs == []
    assert any("boss_one" in r and "no creature" in r for r in report)
