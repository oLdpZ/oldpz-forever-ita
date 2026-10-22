"""A machine-drafted Italian quest line whose English changes goes stale on `check`, and the generated
quest shard ships it with the stale status code (Review Focus 3 of the 1–20 quest plan)."""

import shutil
from pathlib import Path

from wfj.cmd import check, generate
from wfj.core.hashing import key
from wfj.core.normalize import normalize_v1
from wfj.emit import schema
from wfj.io.jsonl_store import Store

QUEST, FIELD = 2, "title"
NEW_EN = "Sharptalon's Sharp Claw"


def _store(root: Path, tmp_path: Path, monkeypatch) -> Path:
    shutil.copytree(root / "tests" / "fixtures" / "it-store", tmp_path / "repo")
    monkeypatch.chdir(tmp_path / "repo")
    return tmp_path / "repo" / "data"


def _line(store: Store, field: str) -> dict:
    return next(ln for ln in store.load("quest") if ln["id"] == QUEST and ln["field"] == field)


def _row(root: Path, data: Path) -> str:
    planned = generate.plan(Store(data), generate.vectors_rows(root / "data"), {})
    shard = next(text for path, text in planned.items() if path.startswith("Data/Quest/") and f"[{QUEST}] = " in text)
    return next(ln for ln in shard.splitlines() if ln.lstrip().startswith(f"[{QUEST}] = "))


def test_changed_english_makes_a_machine_quest_line_stale_and_the_shard_marks_it(root, tmp_path, monkeypatch):
    data = _store(root, tmp_path, monkeypatch)
    store, english = Store(data), Store(data, english=True)
    before = _line(store, FIELD)
    assert before["provenance"]["class"] == "machine" and "it" in before
    assert check.run([]) == 0
    assert _line(store, FIELD)["status"] == "trusted"
    fields = [f for f in ("title", "objectives", "description", "progress", "completion")
              if any(ln["id"] == QUEST and ln["field"] == f for ln in store.load("quest"))]
    trusted = schema.STATUS_CHAR["trusted"]
    assert _row(root, data).endswith(f'"{trusted * len(fields)}" }},')

    # the English title is reworded upstream: a new hash in data/english
    rows = english.load("quest")
    for ln in rows:
        if ln["id"] == QUEST and ln["field"] == FIELD:
            ln["en"], ln["hash"] = NEW_EN, key(normalize_v1(NEW_EN))
    english.save("quest", rows)

    assert check.run([]) == 0
    after = _line(store, FIELD)
    assert after["status"] == "stale"
    assert after["english"]["hash"] == before["english"]["hash"]  # sticky: the hash it was checked against
    assert all(_line(store, f)["status"] == "trusted" for f in fields if f != FIELD)
    assert check.run([]) == 0 and _line(store, FIELD)["status"] == "stale"  # stays stale on a rerun

    codes = "".join(schema.STATUS_CHAR["stale"] if f == FIELD else trusted for f in fields)
    row = _row(root, data)
    assert row.endswith(f'"{codes}" }},')
    assert f"0x{before['english']['hash'][:8]}" in row  # the shard keeps the sticky hash
