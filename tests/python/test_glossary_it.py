"""The official EN→IT glossary (`pipeline/glossario_ufficiale.tsv`): Blizzard's Italian names of zones, factions,
classes, races, items and spells, taken only where the retail English is Forever's; `translate_batch cut`
attaches the terms a row's English holds, and `translate_lint` warns when a draft drops one."""

import json
from pathlib import Path

import pytest

from wfj.core.hashing import key as hash_key
from wfj.core.model import english_line
from wfj.core.normalize import normalize_for
from wfj.dev import glossary_it as gl
from wfj.dev import translate_batch as tb
from wfj.dev import translate_lint as tl
from wfj.io.jsonl_store import Store

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RETAIL = FIXTURES / "retail"
FOREVER = FIXTURES / "forever-names"


def _english(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    en = Store(data, english=True)

    def line(id_, field, text):
        return english_line(id_, field, text, hash_key(normalize_for("item", text)), "db2@1.60.1.70450")

    en.save("item", [line(117, "name", "Tough Jerky"), line(118, "name", "Other")])
    en.save("spell", [line(100, "name", "Charge"), line(133, "name", "Fire Blast"), line(134, "name", "Frost Shock")])
    return data


def test_build_glossary_takes_only_the_same_english_with_other_italian(tmp_path):
    terms = gl.build_glossary(RETAIL, _english(tmp_path) / "english", FOREVER)
    got = {(k, i): (en, it) for k, i, en, it in terms}
    assert got[("zona", 1519)] == ("Stormwind City", "Roccavento")
    assert got[("zona", 1537)] == ("Ironforge", "Forgiardente")
    assert ("zona", 1637) not in got  # Orgrimmar is Orgrimmar in Italian too
    assert ("zona", 14) not in got  # retail renamed it: not Forever's Durotar
    assert got[("fazione", 72)] == ("Stormwind", "Roccavento")
    assert got[("oggetto", 117)] == ("Tough Jerky", "Carne Secca Dura")
    assert got[("abilita", 133)] == ("Fire Blast", "Deflagrazione di Fuoco")
    assert ("abilita", 134) not in got  # Forever's spell 134 is another spell
    # a one-word item or spell name is a common word ("Charge", "Other"): left out
    assert ("abilita", 100) not in got and ("oggetto", 118) not in got
    # classes and races in both forms
    assert ("classe", 5, "Priest", "Sacerdote") in terms
    assert ("classe", 5, "Priest", "Sacerdotessa") in terms
    assert ("razza", 4, "Night Elf", "Elfa della Notte") in terms
    assert not any(t[0] == "razza" and t[2] == "Tauren" for t in terms)


def test_write_and_read_round_trip(tmp_path):
    terms = gl.build_glossary(RETAIL, _english(tmp_path) / "english", FOREVER)
    out = tmp_path / "glossario_ufficiale.tsv"
    gl.write_glossary(out, terms)
    assert out.read_text(encoding="utf-8").splitlines()[0] == "tipo\tid\ten\tit"
    assert gl.read_glossary(out) == terms


def test_the_matcher_prefers_the_longest_term_and_whole_words():
    m = gl.Matcher([("zona", 1519, "Stormwind City", "Roccavento"), ("fazione", 72, "Stormwind", "Roccavento"),
                    ("zona", 1537, "Ironforge", "Forgiardente"), ("classe", 5, "Priest", "Sacerdote"),
                    ("classe", 5, "Priest", "Sacerdotessa")])
    assert m.find("Go to Stormwind City.") == [["Stormwind City", "Roccavento", "zona"]]
    assert m.find("Stormwind guards and Ironforge.") == [["Stormwind", "Roccavento", "fazione"], ["Ironforge", "Forgiardente", "zona"]]
    assert m.find("Ironforged steel, Priestess.") == []
    assert m.find("Ask a Priest.") == [["Priest", "Sacerdote", "classe"], ["Priest", "Sacerdotessa", "classe"]]


def test_cut_attaches_the_glossary_terms(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    (tmp_path / "docs" / "content").mkdir(parents=True)
    (tmp_path / "docs" / "content" / "translation-style-guide.md").write_text("# guide\n\nversion: sg1\n")
    (tmp_path / "pipeline").mkdir()
    gl.write_glossary(tmp_path / "pipeline" / gl.GLOSSARY, [("zona", 1519, "Stormwind City", "Roccavento")])
    Store(data, english=True).save("quest", [
        {"id": 1, "field": "progress", "en": "Go to Stormwind City.", "hash": "0" * 16, "src": "vmangos@13b49dc"},
        {"id": 2, "field": "progress", "en": "Rest a while.", "hash": "1" * 16, "src": "vmangos@13b49dc"},
    ])
    out = tmp_path / "batch.jsonl"
    rows = {r["en"]: r for r in tb.cut(data, "progress", 10, out)}
    assert rows["Go to Stormwind City."]["glossary"] == [["Stormwind City", "Roccavento", "zona"]]
    assert "glossary" not in rows["Rest a while."]
    written = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert any(r.get("glossary") for r in written)


def test_lint_warns_when_the_italian_drops_a_glossary_term(tmp_path):
    row = {"ref": "r1", "kind": "progress", "en": "Go to Stormwind City.", "targets": [[1, "progress"]],
           "glossary": [["Stormwind City", "Roccavento"]]}
    assert tl.glossary_warnings(row, "Vai a Stormwind City.") == ["glossary_term:Stormwind City→Roccavento"]
    assert tl.glossary_warnings(row, "Vai a Roccavento.") == []
    # a warning, not a failure: the row still passes
    batch, draft = tmp_path / "b.jsonl", tmp_path / "d.jsonl"
    tb.write_jsonl(batch, [row])
    tb.write_jsonl(draft, [{"ref": "r1", "it": "Vai a Stormwind City."}])
    ok, failures = tl.lint(batch, draft, set())
    assert failures == {} and len(ok) == 1
    assert tl.warnings(batch, draft) == {"r1": ["glossary_term:Stormwind City→Roccavento"]}
    # either form of a class or race word will do
    two = {**row, "en": "Ask a Priest.", "glossary": [["Priest", "Sacerdote"], ["Priest", "Sacerdotessa"]]}
    assert tl.glossary_warnings(two, "Chiedi a una sacerdotessa.") == []


def test_a_one_word_name_mostly_written_lower_case_is_a_common_word(tmp_path):
    data = _english(tmp_path)
    # the English corpus says "lighthouse" far more often than it names the Lighthouse
    Store(data, english=True).save("quest", [
        {"id": i, "field": "description", "en": f"Climb the lighthouse {i}. The Lighthouse.", "hash": f"{i:016x}",
         "src": "vmangos@13b49dc"} if i == 1 else
        {"id": i, "field": "description", "en": f"Climb the lighthouse {i}.", "hash": f"{i:016x}",
         "src": "vmangos@13b49dc"}
        for i in range(1, 7)
    ])
    got = {(k, i) for k, i, _, _ in gl.build_glossary(RETAIL, data / "english", FOREVER)}
    assert ("zona", 26) not in got
    assert ("zona", 1537) in got  # Ironforge: never written lower case


DERIVED_HEADER = "tipo\tid\ten\tit\tda\n"
OFFICIAL = [("zona", 9, "Northshire Valley", "Valle della Contea del Nord"),
            ("zona", 1519, "Stormwind City", "Roccavento")]


def _derived_repo(tmp_path, rows: str) -> Path:
    (tmp_path / "pipeline").mkdir(exist_ok=True)
    gl.write_glossary(tmp_path / "pipeline" / gl.GLOSSARY, OFFICIAL)
    (tmp_path / "pipeline" / gl.DERIVED).write_text(DERIVED_HEADER + rows, encoding="utf-8")
    return tmp_path


def test_derived_terms_are_loaded_with_the_official_glossary(tmp_path):
    repo = _derived_repo(tmp_path, "zona\t9\tNorthshire\tContea del Nord\tNorthshire Valley\n")
    terms = gl.load_terms(repo)
    assert ("zona", 9, "Northshire", "Contea del Nord") in terms and len(terms) == 3
    m = gl.load_matcher(repo)
    assert m.find("Wolves in Northshire.") == [["Northshire", "Contea del Nord", "zona"]]
    assert m.find("Wolves in Northshire Valley.") == [["Northshire Valley", "Valle della Contea del Nord", "zona"]]


def test_a_derived_italian_not_inside_the_official_italian_is_rejected(tmp_path):
    repo = _derived_repo(tmp_path, "zona\t9\tNorthshire\tContea Settentrionale\tNorthshire Valley\n")
    with pytest.raises(ValueError, match="Contea Settentrionale"):
        gl.load_matcher(repo)


def test_a_derived_term_from_no_official_term_is_rejected(tmp_path):
    for bad in ("zona\t9\tNorthshire\tContea del Nord\tNorthshire Vale\n",  # no such official English
                "zona\t1519\tNorthshire\tContea del Nord\tNorthshire Valley\n",  # wrong id
                "zona\t9\tNorthshire\tContea del Nord\n"):  # no `da` column
        repo = _derived_repo(tmp_path, bad)
        with pytest.raises(ValueError):
            gl.load_terms(repo)


def test_the_committed_derived_glossary_is_valid():
    repo = Path(__file__).resolve().parents[2]
    terms = gl.load_terms(repo)
    assert ("zona", 9, "Northshire", "Contea del Nord") in terms
    derived = gl.read_derived(repo / "pipeline" / gl.DERIVED)
    assert len(derived) >= 1


CURATED_HEADER = "tipo\ten\tit\tnota\n"


def _curated_repo(tmp_path, rows: str) -> Path:
    repo = _derived_repo(tmp_path, "")
    (repo / "pipeline" / gl.CURATED).write_text(CURATED_HEADER + rows, encoding="utf-8")
    return repo


def test_curated_names_are_loaded_by_the_one_loader_as_their_own_kind(tmp_path):
    """`pipeline/glossario_curato.tsv`: names the coordinator decided, not Blizzard's. They load with the
    official and derived terms (kind `curato`), so cut attaches them and the import marks them."""
    repo = _curated_repo(tmp_path, "zona\tThe Barrens\tSavane\tle Savane\norganizzazione\tSI:7\tIR:7\t\n")
    terms = gl.load_terms(repo)
    assert ("curato", 0, "The Barrens", "Savane") in terms and ("curato", 0, "SI:7", "IR:7") in terms
    m = gl.load_matcher(repo)
    assert m.find("Report to SI:7 in Stormwind City.") == [
        ["SI:7", "IR:7", "curato"], ["Stormwind City", "Roccavento", "zona"]]
    from wfj.core import names

    assert names.mark_from_english("Fai rapporto all'IR:7.", "Report to SI:7.", m) == "Fai rapporto all'⟦SI:7=IR:7⟧."


def test_a_curated_name_the_official_glossary_already_has_is_refused(tmp_path):
    for bad in ("zona\tStormwind City\tRoccavento Città\t\n",  # already official
                "zona\tThe Barrens\t\t\n",  # no Italian
                "zona\tThe Barrens\tSavane\n",  # no `nota` column
                "cognome\tProudmoore\tMareforte\t\n"):  # not a kind of name the file holds
        repo = _curated_repo(tmp_path, bad)
        with pytest.raises(ValueError):
            gl.load_terms(repo)


def test_lint_only_warns_for_a_curated_name():
    row = {"ref": "r1", "kind": "progress", "en": "Go to the Mage Quarter.", "targets": [[1, "progress"]],
           "glossary": [["Mage Quarter", "Quartiere dei Maghi", "curato"]]}
    assert tl.glossary_errors(row, "Vai al Mage Quarter.") == []
    assert tl.glossary_warnings(row, "Vai al Mage Quarter.") == ["glossary_term:Mage Quarter→Quartiere dei Maghi"]


def test_the_committed_curated_glossary_is_valid_and_adds_only_new_names():
    repo = Path(__file__).resolve().parents[2]
    terms = gl.load_terms(repo)
    curated = {(en, it) for k, _, en, it in terms if k == gl.CURATED_KIND}
    for pair in [("Mage Quarter", "Quartiere dei Maghi"), ("SI:7", "IR:7"), ("The Barrens", "Savane"),
                 ("Razormane", "Chiomaguzza"), ("Deathstalkers", "Inseguitori della Morte")]:
        assert pair in curated
    others = {en for k, _, en, _ in terms if k != gl.CURATED_KIND}
    assert not {en for en, _ in curated} & others
    # common nouns are not names
    assert not {en for en, _ in curated} & {"furbolg", "moonkin", "voidwalker", "quilboar", "pet"}


CREATURES = ("id\tfield\ten\tit\tfonte\n"
             "448\tname\tHogger\tHogger il Bruto\tdb2\n"
             "416\tname\tImp\tFolletto\tdb2\n"
             "116\tname\tDefias Thug\tTeppista Defias\tdb2\n"
             "117\tname\tDefias Thug Leader\tCapo dei Teppisti Defias\twowhead\n"
             "118\tname\tOld Wording\tVecchia Formulazione\tdb2\n"
             "12696\tname\tSenani Thunderheart\tSenani Cuore Tonante\tdb2\n"
             "12696\tsubname\tWarsong Outriders\tEsploratori Cantaguerra\tdb2\n")


def _creature_english(tmp_path: Path) -> tuple[Path, Path]:
    data = _english(tmp_path)

    def line(id_, field, text):
        return english_line(id_, field, text, hash_key(normalize_for("item", text)), "vmangos@4641790")

    Store(data, english=True).save("unit", [
        line(448, "name", "Hogger"), line(416, "name", "Imp"), line(116, "name", "Defias Thug"),
        line(117, "name", "Defias Thug Leader"), line(118, "name", "New Wording"),
        line(12696, "name", "Senani Thunderheart"), line(12696, "subname", "Warsong Outriders"),
    ])
    # "imp" is a common word in the corpus; "hogger" never written lower case
    Store(data, english=True).save("quest", [
        {"id": 1, "field": "description", "en": "Kill Hogger and the imp.", "hash": "0" * 16,
         "src": "vmangos@13b49dc"}])
    tsv = tmp_path / "creature_official.tsv"
    tsv.write_text(CREATURES, encoding="utf-8")
    return data, tsv


def test_glossary_reads_creatura(tmp_path):
    data, tsv = _creature_english(tmp_path)
    terms = gl.build_glossary(RETAIL, data / "english", FOREVER, creatures=tsv)
    creatura = {(i, en, it) for k, i, en, it in terms if k == "creatura"}
    assert (12696, "Senani Thunderheart", "Senani Cuore Tonante") in creatura
    assert (448, "Hogger", "Hogger il Bruto") in creatura  # one word, never lower case: a proper name
    assert not any(en == "Imp" for _, en, _ in creatura)  # one word the corpus writes lower case: dropped
    assert not any(i == 118 for i, _, _ in creatura)  # the English is no longer Forever's
    assert not any(en == "Warsong Outriders" for _, en, _ in creatura)  # only names, not subnames
    out = tmp_path / "glossario_ufficiale.tsv"
    gl.write_glossary(out, terms)
    assert gl.read_glossary(out) == terms
    m = gl.Matcher(gl.read_glossary(out))
    assert m.find("Speak with Senani Thunderheart.") == [["Senani Thunderheart", "Senani Cuore Tonante", "creatura"]]


def test_the_matcher_takes_the_longest_creature_name():
    m = gl.Matcher([("creatura", 116, "Defias Thug", "Teppista Defias"),
                    ("creatura", 117, "Defias Thug Leader", "Capo dei Teppisti Defias")])
    assert m.find("Slay the Defias Thug Leader.") == [["Defias Thug Leader", "Capo dei Teppisti Defias", "creatura"]]
    assert m.find("Slay a Defias Thug.") == [["Defias Thug", "Teppista Defias", "creatura"]]
    assert m.find("Slay a defias thug.") == []  # case-sensitive


def test_creatura_comes_after_zona_in_the_matcher_order():
    assert gl.ORDER.index("zona") < gl.ORDER.index("creatura") < gl.ORDER.index("fazione")


def test_lint_only_warns_for_a_creature_name():
    # until the phase-2 realignment the existing texts keep many NPC names in English: a warning, not a failure
    row = {"ref": "r1", "kind": "progress", "en": "Speak with Senani Thunderheart.", "targets": [[1, "progress"]],
           "glossary": [["Senani Thunderheart", "Senani Cuore Tonante", "creatura"]]}
    assert tl.glossary_errors(row, "Parla con Senani Thunderheart.") == []
    assert tl.glossary_warnings(row, "Parla con Senani Thunderheart.") == [
        "glossary_term:Senani Thunderheart→Senani Cuore Tonante"]
    assert tl.glossary_warnings(row, "Parla con Senani Cuore Tonante.") == []


def test_npc_names_do_not_count_as_capitalised_words(tmp_path):
    # a title-cased NPC name ("Frenzy") says nothing about how prose writes the word
    data, _ = _creature_english(tmp_path)
    Store(data, english=True).save("unit", [
        english_line(i, "name", "Frenzy", hash_key(normalize_for("item", "Frenzy")), "vmangos@4641790")
        for i in range(1, 6)])
    counts = gl.word_counts(Store(data, english=True))
    assert counts["Frenzy"] == 0 and counts["Hogger"] == 1
