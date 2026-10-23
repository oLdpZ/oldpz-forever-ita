"""English NPC names and titles from the VMaNGOS world database: `data/english/unit`.

    python -m wfj.dev.unit_english --db <mangos.sqlite> [--commit 4641790] [--data <data root>]

One `name` line per creature with a non-empty name, and one `subname` line (the title under the name,
"Weapon Merchant") where it is non-empty, from the creature's highest-patch row. The addon looks a unit up by
the id in its GUID and shows the Italian name; this is the English that translation is checked against.

A line a client recorded in game (the collector) keeps its (id, field): what Forever shows is the English,
VMaNGOS is a stand-in (ADR-053). The vmangos lines are replaced as a set on every run."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from wfj.cmd.import_english import merge_source, source_name
from wfj.core.hashing import key as hash_key
from wfj.core.model import english_line
from wfj.core.normalize import normalize_for
from wfj.io import vmangos
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

DEFAULT_COMMIT = "4641790"
FIELDS = ("name", "subname")


def build(
    creatures: dict[int, dict[str, Any]],
    existing: list[dict[str, Any]],
    src: str = f"vmangos@{DEFAULT_COMMIT}",
) -> list[dict[str, Any]]:
    """The vmangos English lines for `creatures`, minus those whose (id, field) a collector line holds."""
    held = {(ln["id"], ln["field"]) for ln in existing if source_name(ln) == "collector"}
    rows: list[dict[str, Any]] = []
    for id_, c in sorted(creatures.items()):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        for field in FIELDS:
            en = name if field == "name" else (c.get("subname") or "").strip()
            if not en or (id_, field) in held:
                continue
            rows.append(english_line(id_, field, en, hash_key(normalize_for("unit", en)), src))
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj.dev.unit_english", description=__doc__.split("\n", 1)[0])
    p.add_argument("--db", type=Path, required=True, help="VMaNGOS mangos.sqlite")
    p.add_argument("--commit", default=DEFAULT_COMMIT, help="VMaNGOS commit the database is built from")
    p.add_argument("--data", type=Path, default=None, help="data root (default: the repo's data/)")
    a = p.parse_args(argv)
    store = Store(a.data or data_root(), english=True)
    existing = store.load("unit")
    rows = build(vmangos.read_creatures(a.db), existing, f"vmangos@{a.commit}")
    merged = merge_source("unit", existing, rows, "vmangos", outranked_by=("collector",))
    store.save("unit", merged)
    names = sum(1 for r in rows if r["field"] == "name")
    print(f"unit-english: {names} names, {len(rows) - names} titles ({len(merged)} lines in all)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
