"""An empty translation store is a valid store: `generate` writes Meta with every count 0 and no shard."""

import re
from pathlib import Path

from wfj.cmd import generate
from wfj.emit import schema
from wfj.io.jsonl_store import Store


def test_generate_with_no_translations(root: Path, tmp_path: Path):
    data = tmp_path / "data"
    (data / "english").mkdir(parents=True)
    (data / "SCHEMA").write_text("1\n", encoding="utf-8")
    report: dict = {}
    planned = generate.plan(Store(data), generate.vectors_rows(root / "data"), report)
    assert set(planned) == {"Data/Meta.lua", "Data/Vectors.lua", "Data/Placeholders.lua"}
    counts = re.search(r"counts = \{ (.*) \}", planned["Data/Meta.lua"]).group(1)
    assert counts == ", ".join(f"{t} = 0" for t in schema.TOC_ORDER)
