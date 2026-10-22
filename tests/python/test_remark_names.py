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
