"""ADR-101: an Italian line is aligned on its numbers only; every Italian word is Latin, so no name check."""

from wfj.core import align
from wfj.core.status import Scope, decide

P = {"class": "human", "translator": "a", "source": "cqjt@1234567", "imported": "2026-09-13"}
EN = "Bring 8 Wolf Pelts to Stormwind."
QUEST = Scope("quest", {"objectives": EN}, "pfquest@1")


def _line(it):
    return {"id": 2, "field": "objectives", "it": it, "status": "pending", "checks": [], "provenance": P,
            "english": None, "reasons": [], "conflicts": []}


def test_italian_words_are_not_names_the_english_must_hold():
    d = decide(_line("Porta 8 Pelli di Lupo a Roccavento."), QUEST, set(), "h")
    assert (d.status, d.reasons, d.checks) == ("trusted", [], ["numbers"])


def test_a_changed_number_is_still_refused():
    d = decide(_line("Porta 9 Pelli di Lupo a Roccavento."), QUEST, set(), "h")
    assert (d.status, d.reasons) == ("rejected", ["numbers_changed:9"])


def test_branch_variants_are_told_apart_by_numbers_not_words():
    # the twin of Align.checkVariants: Italian words never make a variant "write a name its English lacks"
    texts = ["Porta 8 Pelli di Lupo.", "Porta 8 Pelli di Lupo a Roccavento."]
    assert align.indistinguishable(texts, [EN, EN], ["1/0", "1/0"], set()) == [(0, 1), (1, 0)]


def test_a_marked_name_is_judged_on_the_resolved_text():
    # spec §8: `check` reads the Italian a player reads; the English half of a marker is no number, word or
    # length of the translation
    scope = Scope("quest", {"objectives": "Bring 8 Wolf Pelts to Sector 7."}, "pfquest@1")
    d = decide(_line("Porta 8 Pelli di Lupo al ⟦Sector 7=Settore 7⟧."), scope, set(), "h")
    assert (d.status, d.reasons) == ("trusted", [])
    only_name = Scope("quest", {"title": "Stormwind City"}, "pfquest@1")
    line = _line("⟦Stormwind City=Roccavento⟧")
    line["field"] = "title"
    assert decide(line, only_name, set(), "h").status == "trusted"
