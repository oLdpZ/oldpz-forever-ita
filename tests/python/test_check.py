import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from wfj.cmd.check import build_scopes, check_type, english_hash, run, vanilla_ids
from wfj.core import report
from wfj.core.align import check_numbers, load_allowlist
from wfj.core.model import validate_line
from wfj.io.jsonl_store import Store


def _seed(root, tmp_path: Path, monkeypatch):
    """A tiny data/: the seed Italian (tests/fixtures/seed-data), then the English via the real importers."""
    from wfj.cmd import import_

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "SCHEMA").write_text("1\n")
    (tmp_path / "pipeline").mkdir()
    (tmp_path / "pipeline" / "allowlist.txt").write_text(
        (root / "pipeline/allowlist.txt").read_text(encoding="utf-8"), encoding="utf-8"
    )
    # the Italian a predecessor import once wrote from tests/fixtures/predecessor (that importer is gone)
    for type_ in ("quest", "item", "spell"):
        shutil.copytree(root / "tests/fixtures/seed-data" / type_, tmp_path / "data" / type_)
    monkeypatch.chdir(tmp_path)
    assert (
        import_.run(
            [
                "english",
                "pfquest",
                str(root / "tests/fixtures/pfquest/quests.excerpt.lua"),
                "--commit",
                "7786596",
            ]
        )
        == 0
    )
    fx = root / "tests/fixtures/wago"
    assert (
        import_.run(
            [
                "english",
                "wago-ids",
                str(fx / "ItemSparse.excerpt.csv"),
                str(fx / "SpellName.excerpt.csv"),
                "--build",
                "1.15.9.69722",
            ]
        )
        == 0
    )
    return tmp_path / "data"


def test_check_fixture_run_idempotent_and_valid(root, tmp_path: Path, monkeypatch, capsys):
    data = _seed(root, tmp_path, monkeypatch)
    assert run(["--report"]) == 0
    out = capsys.readouterr().out
    assert "vanilla quests with a trusted description" in out and "quest  description" in out
    first = {p.name: p.read_bytes() for p in data.rglob("*.jsonl")}
    assert run([]) == 0
    second = {p.name: p.read_bytes() for p in data.rglob("*.jsonl")}
    assert first == second
    store = Store(data)
    for type_ in ("quest", "item", "spell"):
        for ln in store.load(type_):
            assert ln["status"] != "pending"
            assert validate_line(type_, ln) == []
            if "no_english_id" not in ln["reasons"]:
                assert ln["english"] and len(ln["english"]["hash"]) == 16
    quests = {(ln["id"], ln["field"]): ln for ln in store.load("quest")}
    assert quests[(2, "title")]["status"] == "trusted"
    # Silverwind Refuge vs Splintertree Post (Cataclysm rename): no longer a reason, no name check (ADR-101)
    assert not any(r.startswith("alignment_failed") for r in quests[(2, "description")]["reasons"])
    items = {ln["id"]: ln for ln in store.load("item")}
    assert items[117]["status"] == "unaligned"
    item_scope = build_scopes(Store(data, english=True), "item")[117]
    assert (
        items[117]["english"]["hash"] == english_hash(item_scope, "description") == item_scope.hashes["name"]
    )


def test_stats_reads_only(root, tmp_path: Path, monkeypatch, capsys):
    from wfj.cmd import stats

    data = _seed(root, tmp_path, monkeypatch)
    assert run([]) == 0
    before = {p.name: p.read_bytes() for p in data.rglob("*.jsonl")}
    assert stats.run([]) == 0
    assert "quest  title" in capsys.readouterr().out
    assert before == {p.name: p.read_bytes() for p in data.rglob("*.jsonl")}


def test_report_render_shape():
    t = report.tally(
        {
            "quest": [
                {"field": "title", "status": "trusted", "reasons": [], "checks": ["names"], "conflicts": []},
                {
                    "field": "title",
                    "status": "rejected",
                    "reasons": ["alignment_failed:X"],
                    "checks": [],
                    "conflicts": [{}],
                },
            ]
        }
    )
    txt = report.render(t, {"x": 1})
    assert "quest  title" in txt and "alignment_failed=1" in txt and "x: 1" in txt
    assert t["conflicts"]["quest"] == 1 and t["checks_empty"]["quest"] == 0


def test_committed_data_has_no_pending_and_known_corpus_facts(root):
    store = Store(root / "data")
    lines = store.load("quest")
    if not lines:
        return
    assert not any(ln["status"] == "pending" for ln in lines)
    nj = sorted((ln["id"], ln["field"]) for ln in lines if "not_italian" in ln["reasons"] and ln["english"])
    # 5126 progress is the English "..." drafted as "……": no kana or kanji, but check accepts a dots-only line
    # for dots-only English (the lint's rule), so it ships. Latin-only hand-written text (225 and 1822
    # completion, 4062 and 6681 description) is `not_italian`, so it is ruled `reject` and a draft ships instead.
    assert nj == []
    english = Store(root / "data", english=True)
    vanilla = vanilla_ids(english)
    h = report.headline({"quest": lines}, vanilla)
    # the Italian store grows batch by batch, so no fixed count: every description that ships belongs to a quest
    # the client serves (batches are cut from the served English), so the headline counts all of them
    shipped = {ln["id"] for ln in lines if ln["field"] == "description" and ln["status"] in ("trusted", "stale")}
    assert h["vanilla quests with a trusted description"] == len(shipped)
    # every shipped line records the English it translates (check ran on it)
    assert all(ln["english"] for ln in lines if ln["status"] in ("trusted", "stale"))
    # every truncated description has a whole draft (2922 / 8984, where "rogue" is not the
    # class, pass through a not-names row)
    assert h["vanilla quests whose description was rejected as truncated"] == 0
    hashes = {(ln["id"], ln["field"]): ln["hash"] for ln in english.load("quest")}
    own = [ln for ln in lines if (ln["id"], ln["field"]) in hashes and ln["english"]]
    assert all(
        ln["english"]["hash"] == hashes[(ln["id"], ln["field"])] for ln in own if ln["status"] != "stale"
    )


def test_cli_check_and_stats_registered(root):
    out = subprocess.run(
        [sys.executable, "-m", "wfj", "--help"], cwd=root / "pipeline", capture_output=True, text=True,check=False,
    ).stdout
    assert "check" in out and "stats" in out
    assert check_type([], {}, load_allowlist("")) == []


def test_stale_is_sticky_across_runs(root, tmp_path: Path, monkeypatch):
    """After the English changes, a line stays `stale` on every rerun (its stored
    hash is kept) until an audit rewrites it; a numeric change rejects instead."""
    import json

    from wfj.core.hashing import key
    from wfj.core.normalize import normalize_v1

    data = _seed(root, tmp_path, monkeypatch)
    assert run([]) == 0
    english = Store(data, english=True)
    en = english.load("quest")
    for ln in en:
        if ln["id"] == 2 and ln["field"] == "title":
            ln["en"] = "Sharptalon's Talon"  # non-numeric edit
            ln["hash"] = key(normalize_v1(ln["en"]))
    english.save("quest", en)
    assert run([]) == 0
    first = json.loads((data / "quest/quest-0000.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert (first["id"], first["field"], first["status"]) == (2, "title", "stale")
    old_hash = first["english"]["hash"]
    assert run([]) == 0
    again = json.loads((data / "quest/quest-0000.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert again["status"] == "stale" and again["english"]["hash"] == old_hash


def test_check_refuses_invalid_ruling(root, tmp_path: Path, monkeypatch):
    import json

    import pytest

    data = _seed(root, tmp_path, monkeypatch)
    path = data / "quest/quest-0000.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["ruling"] = {"ruling": "Accept"}  # wrong case, missing by/date
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    with pytest.raises(SystemExit, match="invalid line"):
        run([])


def test_check_refuses_when_english_is_missing(root, tmp_path: Path, monkeypatch):
    data = _seed(root, tmp_path, monkeypatch)
    shutil.rmtree(data / "english" / "quest")
    before = {p.name: p.read_bytes() for p in data.rglob("*.jsonl")}
    with pytest.raises(SystemExit, match="data/english/quest is empty"):
        run([])
    assert {p.name: p.read_bytes() for p in data.rglob("*.jsonl")} == before


def test_scope_is_normalized_so_counts_after_break_are_numbers(root, tmp_path: Path, monkeypatch):
    data = _seed(root, tmp_path, monkeypatch)
    english = Store(data, english=True)
    rows = english.load("quest")
    for ln in rows:
        if ln["field"] == "objectives":
            ln["en"] = "Bring the following:$B$B12 Giant Eggs$B$B10 pieces of Bear Meat"
            target = ln["id"]
            break
    english.save("quest", rows)
    scope = build_scopes(english, "quest")[target]
    assert "$B" not in scope.fields["objectives"]
    _checked, missing = check_numbers("Giant Egg 12個とBear Meat 10個", scope.text)
    assert missing == []
