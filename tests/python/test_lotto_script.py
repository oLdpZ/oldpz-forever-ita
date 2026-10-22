"""`scripts/lotto.sh`: one translation batch, cut and imported. `taglia` cuts the listed quests' lines of one
kind into pipeline/batches/; `importa` lints every draft of the batch, and only when all pass expands them,
imports them as `machine` lines, then runs check, generate and the coverage report (docs/operations/coverage.md
and the counts in README.md / docs/curseforge.md), so every import leaves the generated docs current. A draft with a missing or a duplicated ref
leaves the store and the addon exactly as they were."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from wfj.core.hashing import key as hash_key
from wfj.core.normalize import normalize_v1
from wfj.dev.translate_batch import style_version
from wfj.io.jsonl_store import Store

REPO = Path(__file__).resolve().parents[2]
SG = style_version(REPO)  # the guide's current version, which every lot's draft name ends with
SCRIPT = REPO / "scripts" / "lotto.sh"
ENGLISH = {
    101: "Bring me the wolf pelts, $N. The farm needs them.",
    102: "The forest is quiet tonight.",
    103: "Speak with the guard at the gate.",
}
ITALIAN = {
    "Bring me the wolf pelts, {name}. The farm needs them.": "Portami le pelli di lupo, {name}. Alla fattoria servono.",
    "The forest is quiet tonight.": "La foresta è tranquilla stanotte.",
}

GOSSIP = {  # text hash → English
    "0123456789abcdef": "Welcome, traveler. The inn is open.",
    "fedcba9876543210": "The mayor is not in today.",
}


@pytest.fixture
def repo(tmp_path):
    """A repository with its own data/ (three quests' English, no Italian), style guide and addon."""
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    shutil.copy(REPO / "data" / "SCHEMA", root / "data" / "SCHEMA")
    (root / "docs" / "content").mkdir(parents=True)
    shutil.copy(REPO / "docs/content/translation-style-guide.md", root / "docs/content/translation-style-guide.md")
    (root / "pipeline").mkdir()
    for lst in (REPO / "pipeline").glob("*.txt"):  # allowlist, and the lists the coverage report reads
        shutil.copy(lst, root / "pipeline" / lst.name)
    (root / "docs" / "operations").mkdir()
    for doc in ("README.md", "docs/curseforge.md", "docs/operations/coverage.md"):
        shutil.copy(REPO / doc, root / doc)
    shutil.copytree(REPO / "vectors", root / "vectors")
    shutil.copytree(REPO / "addon", root / "addon")
    Store(root / "data", english=True).save("quest", [
        {"id": i, "field": "description", "en": en, "hash": hash_key(normalize_v1(en)), "src": "wdb@1.60.1.70450"}
        for i, en in ENGLISH.items()
    ])
    Store(root / "data", english=True).save("gossip", [
        {"id": gid, "field": "text", "en": en, "hash": gid, "src": "gossip"} for gid, en in GOSSIP.items()
    ])
    Store(root / "data", english=True).save("objective", [
        {"id": 501, "field": "text", "en": "Wolf pelts collected",
         "hash": hash_key(normalize_v1("Wolf pelts collected")), "src": "wdb@1.60.1.70450"},
    ])
    (root / "ids.txt").write_text("101\n102  # the second quest\n", encoding="utf-8")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "LOTTO_ROOT": str(root), "PY": sys.executable, "LOTTO_DATE": "2026-10-21"}
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, check=False)


def _tree(*folders: Path) -> dict[str, str]:
    return {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for f in folders for p in sorted(f.rglob("*")) if p.is_file()
    }


def _tree_files(*files: Path) -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def _cut(root: Path) -> list[dict]:
    r = _run(root, "taglia", "quest_description", "prova", str(root / "ids.txt"), "10")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2" in r.stdout
    batch = root / "pipeline" / "batches" / "prova.quest_description.jsonl"
    return [json.loads(x) for x in batch.read_text(encoding="utf-8").splitlines()]


def _write_draft(root: Path, rows: list[dict]) -> None:
    draft = root / "pipeline" / "batches" / "prova.quest_description.draft.jsonl"
    draft.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_a_valid_draft_is_imported_checked_and_generated(repo):
    rows = _cut(repo)
    assert sorted(t[0] for r in rows for t in r["targets"]) == [101, 102]
    _write_draft(repo, [{"ref": r["ref"], "it": ITALIAN[r["en"]]} for r in rows])
    r = _run(repo, "importa", "prova")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = Store(repo / "data").load("quest")
    assert sorted(ln["id"] for ln in lines) == [101, 102]
    for ln in lines:
        assert ln["provenance"]["class"] == "machine"
        assert ln["provenance"]["source"] == f"draft-prova-sg{SG}@2026-10-21"
        assert ln["provenance"]["model"] == "claude-opus-5-5"
        assert ln["english"] is not None  # check ran: the line records the English it translates
    data_dir = repo / "addon" / "OldpZ_ForeverITA" / "Data"
    shipped = "".join(p.read_text(encoding="utf-8") for p in data_dir.rglob("*.lua"))
    assert "Portami le pelli di lupo" in shipped
    # the generated docs follow the import: the report counts the two shipped descriptions
    from wfj.dev import counts, coverage

    report = (repo / "docs" / "operations" / "coverage.md").read_text(encoding="utf-8")
    strip = lambda text: [ln for ln in text.splitlines() if not ln.startswith("> **Generated**")]  # noqa: E731
    assert strip(report) == strip(coverage.render(coverage.measure(repo / "data"), "X"))
    readme = (repo / counts.README).read_text(encoding="utf-8")
    assert counts.apply_readme(readme, counts.measure(repo)) == readme


def test_a_failing_coverage_report_restores_data_the_addon_and_the_docs(repo):
    rows = _cut(repo)
    _write_draft(repo, [{"ref": r["ref"], "it": ITALIAN[r["en"]]} for r in rows])
    with (repo / "pipeline" / "served_dispositions.txt").open("w", encoding="utf-8") as f:
        f.write("")  # every served column now lacks a disposition: the coverage report refuses
    before = _tree(repo / "data", repo / "addon", repo / "docs") | _tree_files(repo / "README.md")
    r = _run(repo, "importa", "prova")
    assert r.returncode != 0
    assert "ripristino" in r.stderr
    assert _tree(repo / "data", repo / "addon", repo / "docs") | _tree_files(repo / "README.md") == before


@pytest.mark.parametrize("fault", ["missing", "duplicate"])
def test_a_draft_with_a_missing_or_duplicate_ref_changes_nothing(repo, fault):
    rows = _cut(repo)
    draft = [{"ref": r["ref"], "it": ITALIAN[r["en"]]} for r in rows]
    draft = draft[:1] if fault == "missing" else [*draft, draft[0]]
    _write_draft(repo, draft)
    before = _tree(repo / "data", repo / "addon")
    r = _run(repo, "importa", "prova")
    assert r.returncode != 0
    assert fault in r.stdout + r.stderr
    assert _tree(repo / "data", repo / "addon") == before


def test_importa_without_drafts_fails(repo):
    r = _run(repo, "importa", "nessuno")
    assert r.returncode != 0


def test_a_step_failing_after_the_lint_restores_data_and_the_addon(repo):
    rows = _cut(repo)
    _write_draft(repo, [{"ref": r["ref"], "it": ITALIAN[r["en"]]} for r in rows])
    (repo / "addon" / "OldpZ_ForeverITA" / "OldpZ_ForeverITA.toc").unlink()  # generate cannot write the TOC
    before = _tree(repo / "data", repo / "addon")
    r = _run(repo, "importa", "prova")
    assert r.returncode != 0
    assert "ripristino" in r.stderr
    assert _tree(repo / "data", repo / "addon") == before


def test_a_null_row_is_kept_english_not_imported_and_not_cut_again(repo):
    rows = _cut(repo)
    kept = next(r for r in rows if r["en"] == "The forest is quiet tonight.")
    _write_draft(repo, [{"ref": r["ref"], "it": None if r is kept else ITALIAN[r["en"]]} for r in rows])
    r = _run(repo, "importa", "prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 kept_english" in r.stdout
    lines = Store(repo / "data").load("quest")
    assert [ln["id"] for ln in lines] == [101]  # no Italian line for the kept one
    table = (repo / "pipeline" / "keep_english.tsv").read_text(encoding="utf-8")
    assert "quest\t102\tdescription\t" in table
    # cut again: the kept line is not selected (101 is drafted, 102 kept)
    r = _run(repo, "taglia", "quest_description", "dopo", str(repo / "ids.txt"), "10")
    assert r.returncode == 0, r.stdout + r.stderr
    batch = repo / "pipeline" / "batches" / "dopo.quest_description.jsonl"
    assert batch.read_text(encoding="utf-8").strip() == ""
    # the English changes: the decision is stale and the line is cut again
    english = Store(repo / "data", english=True)
    changed = [
        {**ln, "en": "The forest is loud tonight.", "hash": hash_key(normalize_v1("The forest is loud tonight."))}
        if ln["id"] == 102 else ln
        for ln in english.load("quest")
    ]
    english.save("quest", changed)
    r = _run(repo, "taglia", "quest_description", "dopo", str(repo / "ids.txt"), "10")
    assert r.returncode == 0, r.stdout + r.stderr
    again = [json.loads(x) for x in batch.read_text(encoding="utf-8").splitlines()]
    assert [t[0] for x in again for t in x["targets"]] == [102]


def test_a_batch_of_only_kept_rows_imports_nothing_and_succeeds(repo):
    rows = _cut(repo)
    _write_draft(repo, [{"ref": r["ref"], "it": None} for r in rows])
    r = _run(repo, "importa", "prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert Store(repo / "data").load("quest") == []


def _second_lot(root: Path, nome: str, ids: list[int], italian: dict[str, str]) -> None:
    """Cut the listed quests' descriptions as lot `nome` (redrafting already drafted lines) and draft them."""
    (root / f"{nome}.ids").write_text("".join(f"{i}\n" for i in ids), encoding="utf-8")
    batch = root / "pipeline" / "batches" / f"{nome}.quest_description.jsonl"
    env = {**os.environ, "PYTHONPATH": str(REPO / "pipeline")}
    subprocess.run(
        [sys.executable, "-m", "wfj.dev.translate_batch", "cut", "--kind", "quest_description", "--size", "10",
         "--ids", str(root / f"{nome}.ids"), "--redraft", "--out", str(batch)],
        cwd=root, env=env, check=True, capture_output=True, text=True,
    )
    rows = [json.loads(x) for x in batch.read_text(encoding="utf-8").splitlines()]
    assert rows, "nothing cut"
    draft = root / "pipeline" / "batches" / f"{nome}.quest_description.draft.jsonl"
    draft.write_text(
        "".join(json.dumps({"ref": r["ref"], "it": italian[r["en"]]}, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )


def test_a_lot_adding_a_duplicate_conflict_changes_nothing(repo):
    rows = _cut(repo)
    _write_draft(repo, [{"ref": r["ref"], "it": ITALIAN[r["en"]]} for r in rows])
    assert _run(repo, "importa", "prova").returncode == 0
    # another lot gives quest 102 a different Italian: two machine variants, no winner
    _second_lot(repo, "altro", [102], {"The forest is quiet tonight.": "Stanotte il bosco tace."})
    before = _tree(repo / "data", repo / "addon")
    r = _run(repo, "importa", "altro")
    assert r.returncode != 0, r.stdout + r.stderr
    assert "duplicate_conflict" in r.stderr
    assert _tree(repo / "data", repo / "addon") == before


def test_an_existing_conflict_does_not_block_an_unrelated_lot(repo):
    rows = _cut(repo)
    _write_draft(repo, [{"ref": r["ref"], "it": ITALIAN[r["en"]]} for r in rows])
    assert _run(repo, "importa", "prova").returncode == 0
    store = Store(repo / "data")
    lines = store.load("quest")
    for ln in lines:  # 102 already conflicts with a second machine variant
        if ln["id"] == 102:
            ln["conflicts"] = [{"it": "Stanotte il bosco tace.", "provenance": {
                **ln["provenance"], "source": f"draft-vecchio-sg{SG}@2026-10-20"}}]
    store.save("quest", lines)
    env = {**os.environ, "PYTHONPATH": str(REPO / "pipeline")}
    subprocess.run([sys.executable, "-m", "wfj", "check"], cwd=repo, env=env, check=True, capture_output=True)
    assert [ln["status"] for ln in Store(repo / "data").load("quest") if ln["id"] == 102] == ["rejected"]
    _second_lot(repo, "terzo", [103], {"Speak with the guard at the gate.": "Parla con la guardia al cancello."})
    r = _run(repo, "importa", "terzo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert 103 in {ln["id"] for ln in Store(repo / "data").load("quest")}


def _cut_gossip(root: Path, nome: str, ids: list[str]) -> list[dict]:
    (root / f"{nome}.ids").write_text("".join(f"{i}\n" for i in ids), encoding="utf-8")
    r = _run(root, "taglia", "gossip", nome, str(root / f"{nome}.ids"), "50")
    assert r.returncode == 0, r.stdout + r.stderr
    batch = root / "pipeline" / "batches" / f"{nome}.gossip.jsonl"
    return [json.loads(x) for x in batch.read_text(encoding="utf-8").splitlines()]


def _draft_gossip(root: Path, nome: str, rows: list[dict], italian: str) -> None:
    draft = root / "pipeline" / "batches" / f"{nome}.gossip.draft.jsonl"
    draft.write_text("".join(json.dumps({"ref": r["ref"], "it": italian}) + "\n" for r in rows), encoding="utf-8")


def test_a_gossip_lot_is_cut_by_hash_and_imported(repo):
    rows = _cut_gossip(repo, "g1", ["0123456789abcdef"])
    assert [t[0] for r in rows for t in r["targets"]] == ["0123456789abcdef"]
    _draft_gossip(repo, "g1", rows, "Benvenuto, viandante. La locanda è aperta.")
    r = _run(repo, "importa", "g1")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = Store(repo / "data").load("gossip")
    assert [ln["id"] for ln in lines] == ["0123456789abcdef"]
    assert lines[0]["provenance"]["source"] == f"draft-g1-sg{SG}@2026-10-21"


def test_cut_without_ids_takes_every_untranslated_line(repo):
    r = _run(repo, "taglia", "objective", "o1", "-", "50")
    assert r.returncode == 0, r.stdout + r.stderr
    batch = repo / "pipeline" / "batches" / "o1.objective.jsonl"
    rows = [json.loads(x) for x in batch.read_text(encoding="utf-8").splitlines()]
    assert [t[0] for x in rows for t in x["targets"]] == [501]


def test_a_second_gossip_lot_with_the_same_english_changes_nothing(repo):
    rows = _cut_gossip(repo, "g1", ["0123456789abcdef"])
    _draft_gossip(repo, "g1", rows, "Benvenuto, viandante. La locanda è aperta.")
    assert _run(repo, "importa", "g1").returncode == 0
    # `cut` never re-cuts an imported line: the second lot reuses the rows under its own name
    shutil.copy(repo / "pipeline/batches/g1.gossip.jsonl", repo / "pipeline/batches/g2.gossip.jsonl")
    _draft_gossip(repo, "g2", rows, "Benvenuto, straniero. La locanda è aperta.")
    before = _tree(repo / "data", repo / "addon")
    r = _run(repo, "importa", "g2")
    assert r.returncode != 0, r.stdout + r.stderr
    assert _tree(repo / "data", repo / "addon") == before
