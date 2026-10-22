"""The Italian style guide (sg4): its version, the rules the plan fixes, the interface section's six rules, and
interface terms that hold on every shipped UI line."""

import re
from pathlib import Path

import pytest

from wfj.core import language
from wfj.core.report import SHIPPED
from wfj.dev.translate_batch import STYLE_GUIDE, style_version
from wfj.io.jsonl_store import Store

JAPANESE = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")


@pytest.fixture(scope="module")
def guide(root: Path) -> str:
    return (root / STYLE_GUIDE).read_text(encoding="utf-8")


def test_guide_has_a_version(root: Path):
    assert style_version(root) == 4


def test_guide_states_the_italian_rules(guide):
    for heading in ("## Il compito", "## Terminologia ufficiale", '## Il giocatore si dà del "tu"',
                    "## Genere del giocatore", "## Segnaposto, paragrafi e numeri"):
        assert f"\n{heading}\n" in guide, heading
    assert '{"ref": "<il ref della riga>", "it": "<italiano>"}' in guide  # the draft row a model writes
    assert "`<maschile/femminile>`" in guide
    assert "glossario_ufficiale.tsv" in guide
    assert '`{"ref": "…", "it": null}`' in guide  # a line that stays English (translate_lint: kept_english)
    assert not JAPANESE.search(guide)


def test_guide_carries_the_fixed_lexicon(guide):
    section = guide.split("## Lessico fissato (sg4)", 1)
    assert len(section) == 2, "no fixed lexicon section"
    body = section[1].split("\n## ", 1)[0]
    for term in ("| People's Militia | Milizia del Popolo |", "| SI:7 | IR:7 |", "Brigata del Popolo",
                 "Cognomi dei PNG restano inglesi", "Tribù, clan e gruppi",
                 "| Lunar Festival | Celebrazione della Luna |", "forma ufficiale verificabile resta inglese"):
        assert term in body, term


UI_RULES = ("1. Significato nel contesto", "2. Lunghezza che ci stia", "3. Registro", "4. Coerenza",
            "5. Formato intatto", "6. Nomi ufficiali")


def test_guide_has_the_interface_text_rules(guide):
    section = guide.split("## Testo d'interfaccia (stringhe UI)", 1)
    assert len(section) == 2, "no interface text section"
    body = section[1].split("\n## ", 1)[0]
    for rule in UI_RULES:
        assert f"\n### {rule}\n" in body, rule


TERMS_ROW = re.compile(r"^\| ([a-z ,]+) \| ([^|]+?) \| ([^|]+) \|$", re.M)


def _terms(guide: str) -> list[tuple[str, str, str]]:
    table = guide.split("### 4. Coerenza", 1)[1].split("\n### ", 1)[0]
    return TERMS_ROW.findall(table)


def test_interface_terms_are_italian(guide):
    terms = _terms(guide)
    assert len(terms) >= 7
    for english, italian, _ in terms:
        assert language.is_italian(italian, english), english


def test_interface_terms_hold_on_every_shipped_ui_line(guide, root: Path):
    it = {ln["id"]: ln["it"] for ln in Store(root / "data").load("ui") if ln["status"] in SHIPPED}
    en = {ln["id"]: ln["en"] for ln in Store(root / "data", english=True).load("ui")}
    bad = []
    for english, _, others in _terms(guide):
        word = re.compile(r"\b(" + "|".join(re.escape(t.strip()) for t in english.split(",")) + r")s?\b", re.I)
        # an elided Italian word is not the English term: "quest'area" is "questa area"
        wrong = [re.compile(rf"\b{re.escape(o.strip())}\b(?!['’])", re.I) for o in others.split(",")]
        bad += [(k, english) for k, j in it.items() if k in en and word.search(en[k]) and any(w.search(j) for w in wrong)]
    assert bad == []


def test_guide_states_the_dialogue_rules(guide):
    section = guide.split("## Dialoghi dei PNG", 1)
    assert len(section) == 2, "no dialogue section"
    body = section[1].split("\n## ", 1)[0]
    for rule in ("Opzioni di dialogo", "genere di chi parla"):
        assert rule in body, rule
