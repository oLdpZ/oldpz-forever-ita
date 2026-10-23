"""`wfj.dev.remark_names`: the stored Italian re-marked with the current glossary (a term added since the
line was imported gets its `⟦en=it⟧`), every variant of every non-UI type; a second run changes nothing."""

from pathlib import Path

from wfj.dev import glossary_it as gl
from wfj.dev import remark_names
from wfj.io.jsonl_store import Store


def _repo(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    (tmp_path / "pipeline").mkdir()
    gl.write_glossary(tmp_path / "pipeline" / gl.GLOSSARY, [("zona", 1519, "Stormwind City", "Roccavento")])
    (tmp_path / "pipeline" / gl.CURATED).write_text(
        "tipo\ten\tit\tnota\nzona\tThe Barrens\tSavane\t\n", encoding="utf-8")
    en = "Ride from The Barrens to Stormwind City."
    Store(data, english=True).save("quest", [
        {"id": 5, "field": "description", "en": en, "hash": "a" * 16, "src": "wdb@1.60.1.70450"}])
    prov = {"class": "machine", "model": "m", "source": "draft-x-sg1@2026-10-21", "imported": "2026-10-21"}
    Store(data).save("quest", [{
        "id": 5, "field": "description", "it": "Cavalca dalle Savane a ⟦Stormwind City=Roccavento⟧.",
        "status": "rejected", "checks": [], "reasons": ["duplicate_conflict"], "english": None, "provenance": prov,
        "conflicts": [{"it": "Vai dalle Savane a Roccavento.", "provenance": {**prov, "source": "draft-y-sg1@2026-10-21"}}],
    }])
    return data


def test_remark_adds_the_new_terms_markers_once(tmp_path):
    data = _repo(tmp_path)
    assert remark_names.remark(data) == 3  # Savane in both variants, Roccavento in the conflict variant
    ln = Store(data).load("quest")[0]
    assert ln["it"] == "Cavalca dalle ⟦The Barrens=Savane⟧ a ⟦Stormwind City=Roccavento⟧."
    assert ln["conflicts"][0]["it"] == "Vai dalle ⟦The Barrens=Savane⟧ a ⟦Stormwind City=Roccavento⟧."
    assert remark_names.remark(data) == 0


# ── NPC names from the unit table (official and machine), Task 11 ──────────────────────────────────────────

UNIT_PROV = {
    "official": {"class": "official", "source": "wago-itit@12.1.5.70448", "imported": "2026-10-21"},
    "machine": {"class": "machine", "model": "m", "source": "draft-n01-sg14@2026-10-23", "imported": "2026-10-23"},
}


def _unit_repo(tmp_path: Path, units, quests) -> Path:
    """`units`: (id, en, it, class); `quests`: (id, en, it). The glossary holds Stormwind City only."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    (tmp_path / "pipeline").mkdir()
    gl.write_glossary(tmp_path / "pipeline" / gl.GLOSSARY, [("zona", 1519, "Stormwind City", "Roccavento")])
    eng, store = Store(data, english=True), Store(data)
    eng.save("unit", [{"id": i, "field": "name", "en": en, "hash": "b" * 16, "src": "vmangos@4641790"}
                      for i, en, _, _ in units])
    store.save("unit", [{"id": i, "field": "name", "it": it, "status": "trusted", "checks": [], "reasons": [],
                         "english": {"hash": "b" * 16, "src": "vmangos@4641790"}, "provenance": UNIT_PROV[c],
                         "conflicts": []} for i, _, it, c in units])
    eng.save("quest", [{"id": i, "field": "description", "en": en, "hash": "a" * 16, "src": "wdb@1.60.1.70450"}
                       for i, en, _ in quests])
    store.save("quest", [{"id": i, "field": "description", "it": it, "status": "trusted", "checks": [],
                          "reasons": [], "english": None, "provenance": UNIT_PROV["machine"], "conflicts": []}
                         for i, _, it in quests])
    return data


def test_an_npc_name_is_never_marked_as_itself_only_the_names_inside_it(tmp_path):
    data = _unit_repo(tmp_path, [(3, "Flesh Eater", "Mangiatore di Carne", "official"),
                                 (213, "Hungry Dire Wolf", "Metalupo Affamato", "machine")], [])
    gl.write_glossary(tmp_path / "pipeline" / gl.GLOSSARY, [
        ("creatura", 3, "Flesh Eater", "Mangiatore di Carne"), ("creatura", 9, "Dire Wolf", "Metalupo")])
    remark_names.remark(data)
    assert {ln["id"]: ln["it"] for ln in Store(data).load("unit")} == {
        3: "Mangiatore di Carne", 213: "⟦Dire Wolf=Metalupo⟧ Affamato"}


def test_a_name_inside_a_longer_npc_name_with_no_italian_yet_is_left_alone(tmp_path):
    """`Kwee Q. Peddlefeet` has no Italian row yet: the `Peddlefeet` inside it is no NPC of its own, so it is
    never marked there (a marker is never taken back, so a partial one would stay once the long name lands)."""
    data = _unit_repo(tmp_path, [(16085, "Peddlefeet", "Stupìdo", "official")], [
        (1, "I am Kwee Q. Peddlefeet! Ask Peddlefeet.", "Sono Kwee Q. Peddlefeet! Chiedi a Peddlefeet.")])
    eng = Store(data, english=True)
    eng.save("unit", eng.load("unit") + [
        {"id": 16075, "field": "name", "en": "Kwee Q. Peddlefeet", "hash": "c" * 16, "src": "vmangos@4641790"}])
    remark_names.remark(data)
    assert _it(data)[1] == "Sono Kwee Q. Peddlefeet! Chiedi a ⟦Peddlefeet=Stupìdo⟧."


def _it(data: Path) -> dict[int, str]:
    return {ln["id"]: ln["it"] for ln in Store(data).load("quest")}


def test_an_english_npc_name_left_in_the_italian_is_marked_with_the_unit_tables_italian(tmp_path):
    from wfj.core import names

    data = _unit_repo(tmp_path, [(12696, "Senani Thunderheart", "Senani Cuore Tonante", "machine")], [
        (1, "Speak with Senani Thunderheart in Stormwind City.", "Parla con Senani Thunderheart a Roccavento."),
        (2, "Senani Thunderheart waits.", "Senani Cuore Tonante ti aspetta."),
        (3, "Senani Thunderheart waits.", "Qualcuno ti aspetta."),  # the name is not there: prose untouched
    ])
    assert remark_names.remark(data) == 3
    it = _it(data)
    assert it[1] == "Parla con ⟦Senani Thunderheart=Senani Cuore Tonante⟧ a ⟦Stormwind City=Roccavento⟧."
    assert it[2] == "⟦Senani Thunderheart=Senani Cuore Tonante⟧ ti aspetta."
    assert it[3] == "Qualcuno ti aspetta."
    assert Store(data).load("unit")[0]["it"] == "Senani Cuore Tonante"  # the name itself is never marked
    # style "en" gives back the English the line held; style "it" the unit table's name
    assert names.resolve(it[1], "en") == "Parla con Senani Thunderheart a Stormwind City."
    assert names.resolve(it[1], "it") == "Parla con Senani Cuore Tonante a Roccavento."
    assert remark_names.remark(data) == 0  # idempotent


def test_a_name_inside_a_longer_name_marks_only_the_longer_one(tmp_path):
    data = _unit_repo(tmp_path, [(94, "Defias Thug", "Brigante Defias", "official"),
                                 (95, "Defias Thug Leader", "Capo dei Briganti Defias", "machine")], [
        (1, "Kill the Defias Thug Leader.", "Uccidi il Defias Thug Leader."),
        (2, "Kill the Defias Thug Leader.", "Uccidi il Capo dei Briganti Defias."),
        (3, "Kill the Defias Thug Leader and a Defias Thug.", "Uccidi il Defias Thug Leader e un Brigante Defias."),
    ])
    remark_names.remark(data)
    it = _it(data)
    assert it[1] == "Uccidi il ⟦Defias Thug Leader=Capo dei Briganti Defias⟧."
    assert it[2] == "Uccidi il ⟦Defias Thug Leader=Capo dei Briganti Defias⟧."
    assert it[3] == ("Uccidi il ⟦Defias Thug Leader=Capo dei Briganti Defias⟧ e un "
                     "⟦Defias Thug=Brigante Defias⟧.")


def test_unit_terms_prefer_official_then_the_most_common_and_skip_common_words(tmp_path):
    data = _unit_repo(tmp_path, [
        (1, "Gnoll Brute", "Bruto Gnoll", "machine"), (2, "Gnoll Brute", "Gnoll Bruto", "official"),
        (3, "Gnoll Brute", "Bruto Gnoll", "machine"),
        (4, "Kobold Miner", "Minatore Coboldo", "machine"), (5, "Kobold Miner", "Coboldo Minatore", "machine"),
        (6, "Kobold Miner", "Coboldo Minatore", "machine"),
        (7, "Wolf", "Lupo", "official"),  # "wolf" in the corpus: a common word, never a term
        (8, "Hogger", "Hogger", "official"),  # same in both languages: nothing to mark
        (9, "Gruff", "Burbero", "machine"),  # one word never written in lower case: a name
    ], [(1, "The wolf and Gruff.", "Il lupo e Gruff.")])
    conflicts: list[str] = []
    terms = gl.unit_terms(data, gl.word_counts(Store(data, english=True)), conflicts)
    by_en = {en: it for _, _, en, it in terms}
    assert by_en == {"Gnoll Brute": "Gnoll Bruto", "Kobold Miner": "Coboldo Minatore", "Gruff": "Burbero"}
    assert len(conflicts) == 2 and all("Gnoll Brute" in c or "Kobold Miner" in c for c in conflicts)
    remark_names.remark(data)
    assert _it(data)[1] == "Il lupo e ⟦Gruff=Burbero⟧."


# ── stale NPC-name markers and one Italian per English (final review) ─────────────────────────────────────


def _unit_problems(tmp_path: Path, data: Path) -> list[str]:
    from wfj.cmd import validate

    return validate.rule_unit_names(Store(data), Store(data, english=True), tmp_path)


def _make_official(data: Path, id_: int, it: str) -> None:
    """An official row arrives for unit `id_` (as `import official` + `check` leave it: the official text wins,
    the machine draft becomes a conflict)."""
    store = Store(data)
    lines = store.load("unit")
    for ln in lines:
        if ln["id"] == id_:
            ln["conflicts"].append({"it": ln["it"], "provenance": ln["provenance"]})
            ln["it"], ln["provenance"] = it, UNIT_PROV["official"]
    store.save("unit", lines)


def test_a_marker_of_a_machine_form_is_rewritten_when_the_official_name_arrives(tmp_path):
    data = _unit_repo(tmp_path, [(12696, "Senani Thunderheart", "Senani Cuor di Tuono", "machine")], [
        (1, "Speak with Senani Thunderheart.", "Parla con Senani Thunderheart."),
        (2, "Senani Thunderheart waits in Stormwind City.", "Senani Cuor di Tuono ti aspetta a Roccavento."),
    ])
    remark_names.remark(data)
    assert _it(data)[1] == "Parla con ⟦Senani Thunderheart=Senani Cuor di Tuono⟧."
    assert _unit_problems(tmp_path, data) == []
    _make_official(data, 12696, "Senani Cuore Tonante")  # spec §5b: the official form wins and rewrites the texts
    problems = _unit_problems(tmp_path, data)
    assert len(problems) == 2 and all("Senani Thunderheart" in p and "Senani Cuore Tonante" in p for p in problems)
    stats: dict[str, int] = {}
    assert remark_names.remark(data, stats=stats) == 2
    assert stats["rewritten"] == 2
    it = _it(data)
    assert it[1] == "Parla con ⟦Senani Thunderheart=Senani Cuore Tonante⟧."
    assert it[2] == "⟦Senani Thunderheart=Senani Cuore Tonante⟧ ti aspetta a ⟦Stormwind City=Roccavento⟧."
    assert _unit_problems(tmp_path, data) == []
    assert remark_names.remark(data) == 0  # idempotent


def test_a_glossary_marker_is_left_as_it_is(tmp_path):
    """Only NPC-name markers follow the unit table: a glossary term may have several right Italian forms
    (male / female, a derived short form), so its marker is never rewritten here."""
    data = _unit_repo(tmp_path, [], [(1, "Go to Stormwind City.", "Vai a ⟦Stormwind City=Città di Roccavento⟧.")])
    assert remark_names.remark(data) == 0
    assert _it(data)[1] == "Vai a ⟦Stormwind City=Città di Roccavento⟧."
    assert _unit_problems(tmp_path, data) == []


def test_ids_sharing_an_english_name_ship_one_italian(tmp_path):
    """Two creature ids named `Gnoll Brute`: the official form wins for both (the addon's objective index, keyed
    by the English, would otherwise answer nothing on a tie or the wrong name on a majority)."""
    data = _unit_repo(tmp_path, [(1, "Gnoll Brute", "Gnoll Bruto", "official"),
                                 (2, "Gnoll Brute", "Bruto Gnoll", "machine"),
                                 (3, "Gnoll Brute", "Bruto Gnoll", "machine")], [])
    problems = _unit_problems(tmp_path, data)
    assert len(problems) == 1 and "Gnoll Brute" in problems[0] and "unit 2" in problems[0]
    stats: dict[str, int] = {}
    remark_names.remark(data, stats=stats)
    assert stats["harmonised"] == 2
    assert {ln["id"]: ln["it"] for ln in Store(data).load("unit")} == {1: "Gnoll Bruto", 2: "Gnoll Bruto",
                                                                       3: "Gnoll Bruto"}
    assert _unit_problems(tmp_path, data) == []


def test_two_official_names_for_one_english_are_left_to_a_person(tmp_path):
    data = _unit_repo(tmp_path, [(1, "Gnoll Brute", "Gnoll Bruto", "official"),
                                 (2, "Gnoll Brute", "Bruto Gnoll", "official")], [])
    remark_names.remark(data)
    assert {ln["id"]: ln["it"] for ln in Store(data).load("unit")} == {1: "Gnoll Bruto", 2: "Bruto Gnoll"}
    assert len(_unit_problems(tmp_path, data)) == 1
