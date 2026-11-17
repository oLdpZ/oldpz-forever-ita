"""The NPCs' greeting on a click and goodbye (wfj.dev.voice_hello): which voice says them, which English files
the addon silences, and the short Italian lines each voice says."""

from __future__ import annotations

from wfj.dev import voice_hello

PHRASES = {
    "*": {"g": ["Salve.", "Ben trovato.", "Posso aiutarti?"], "b": ["Addio.", "Buona fortuna."],
          "p": ["Basta così!", "Lasciami in pace!"]},
    "orc": {"g": ["Lok'tar!"], "b": ["Lok'tar ogar!"], "p": []},
}
# set 7: an orc voice set (greet kit 70, goodbye 71, annoyed 72); set 8: one no voiced creature uses
SETS = {7: (70, 71, 72), 8: (80, 81, 0)}
KITS = {70: [700, 701], 71: [710], 72: [720], 80: [800], 81: [810]}


def plan(**kw):
    args = dict(greeters=[(1, 7), (2, 7), (3, 7), (4, 8)], cast={1: "genorcm1", 2: "genorcm1", 3: "thrall"},
                races={1: "orc", 2: "orc", 3: "orc"}, sets=SETS, kits=KITS, phrases=PHRASES)
    args.update(kw)
    return voice_hello.plan(**args)


def test_an_npc_greets_with_its_own_voice_and_one_without_a_voice_with_its_set_s_most_common():
    p = plan(greeters=[(1, 7), (2, 7), (3, 7), (5, 7)])
    assert p.greeters == {1: "genorcm1", 2: "genorcm1", 3: "thrall", 5: "genorcm1"}


def test_a_set_no_voiced_npc_uses_stays_english():
    p = plan()
    assert 4 not in p.greeters
    assert 800 not in p.mute and 810 not in p.mute
    assert p.mute == [700, 701, 710, 720]  # every file of the covered set, sorted


def test_an_npc_of_a_set_no_voiced_npc_uses_greets_with_its_race_s_generic_voice():
    p = plan(fallback={4: "gengnomem1"}, races={1: "orc", 2: "orc", 3: "orc", 4: "gnome"})
    assert p.greeters[4] == "gengnomem1"
    assert 800 in p.mute and 810 in p.mute
    assert {r["key"] for r in p.lines if r["voice"] == "gengnomem1"} >= {"n-gengnomem1-g1", "n-gengnomem1-p2"}
    # a generic voice never outvotes a set's own: NPC 5 of set 7 still gets the set's most common voice
    p = plan(greeters=[(1, 7), (5, 7)], fallback={5: "gengnomem1"})
    assert p.greeters[5] == "genorcm1"


def test_a_ruling_wins_over_the_cast_voice_and_the_set_s():
    # an abomination of an undead voice set, cast an undead man's voice: the ruling gives it its own
    p = plan(greeters=[(1, 7), (2, 7), (5, 7)], overrides={2: "abomination", 5: "abomination"})
    assert p.greeters == {1: "genorcm1", 2: "abomination", 5: "abomination"}
    assert "n-abomination-g1" in {r["key"] for r in p.lines}


def test_each_voice_says_three_greetings_two_goodbyes_two_annoyed_lines_its_race_s_first():
    p = plan()
    lines = {r["key"]: r for r in p.lines}
    thrall = [k for k in lines if k.startswith("n-thrall-")]
    assert sorted(thrall) == ["n-thrall-b1", "n-thrall-b2", "n-thrall-g1", "n-thrall-g2", "n-thrall-g3",
                              "n-thrall-p1", "n-thrall-p2"]
    assert lines["n-thrall-g1"]["it"] == "Lok'tar!"
    assert lines["n-thrall-b1"]["it"] == "Lok'tar ogar!"
    assert len({lines[f"n-thrall-g{i}"]["it"] for i in (1, 2, 3)}) == 3  # three different greetings
    assert lines["n-thrall-g1"]["speaker"] == 3 and lines["n-thrall-g1"]["voice"] == "thrall"
    assert lines["n-genorcm1-g1"]["speaker"] == 1  # the lowest creature cast to the voice


def test_the_lines_are_the_same_on_every_run():
    assert plan().lines == plan().lines


def test_read_phrases_takes_race_slot_and_line(tmp_path):
    f = tmp_path / "hello.tsv"
    f.write_text("# race\tslot\tline\n*\tg\tSalve.\norc\tb\tLok'tar ogar!\n", encoding="utf-8")
    assert voice_hello.read_phrases(f) == {"*": {"g": ["Salve."]}, "orc": {"b": ["Lok'tar ogar!"]}}
