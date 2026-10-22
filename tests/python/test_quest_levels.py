"""The quest level table (`make quest-levels`): pfQuest's db/quests.lua gives each quest its `min` / `lvl`;
a quest the English store has and pfQuest lacks (a Forever-only quest) is listed as `assente`, never dropped."""

import json
from pathlib import Path

from wfj.dev import quest_levels

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pfquest-quests-mini.lua"


def _english_store(tmp_path: Path, ids: list[int]) -> Path:
    root = tmp_path / "data"
    folder = root / "english" / "quest"
    folder.mkdir(parents=True)
    rows = [{"id": i, "field": "title", "en": f"Quest {i}", "hash": "0" * 16, "src": "test"} for i in ids]
    by_shard: dict[str, list[str]] = {}
    for r in rows:
        by_shard.setdefault(f"quest-{r['id'] // 1000:04d}.jsonl", []).append(json.dumps(r))
    for name, lines in by_shard.items():
        (folder / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def test_read_levels():
    levels = quest_levels.read_levels(FIXTURE)
    assert levels == {2: (16, 20), 7: (1, 2), 10: (39, 48), 783: (1, 1)}


def test_table_lists_absent_quests_and_ids_up_to(tmp_path):
    data = _english_store(tmp_path, [2, 7, 10, 783, 90001])
    out = tmp_path / "quest_levels.tsv"
    assert quest_levels.main(["--pfquest", str(FIXTURE), "--data", str(data), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "90001\t\t\tassente\n" in text
    assert "7\t1\t2\tpfquest@7786596\n" in text
    assert quest_levels.ids_up_to(20, out) == [2, 7, 783]
    assert quest_levels.ids_up_to(1, out) == [783]


def test_table_skips_pfquest_ids_the_store_lacks(tmp_path):
    data = _english_store(tmp_path, [7])
    out = tmp_path / "quest_levels.tsv"
    quest_levels.main(["--pfquest", str(FIXTURE), "--data", str(data), "--out", str(out)])
    assert quest_levels.ids_up_to(60, out) == [7]
