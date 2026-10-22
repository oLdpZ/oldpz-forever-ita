"""The quest level table: which quests a level band covers, so translation batches are cut by level.

    python -m wfj.dev.quest_levels --pfquest <db/quests.lua> [--data <data/>] --out quest_levels.tsv

The levels come from pfQuest's `db/quests.lua` (`pfDB["quests"]["data"]`, `["min"]` = the level the quest
is offered at, `["lvl"]` = the quest's own level), at the commit the English import pins (`make
quest-levels`). The table lists every quest of `data/english/quest`: a quest pfQuest knows gets its levels
and `fonte` `pfquest@<commit>`; a quest pfQuest lacks (one Forever added) gets empty levels and `fonte`
`assente`, so it is counted apart instead of vanishing from a level band. pfQuest quests the English store
does not hold (Forever does not serve them) are left out. The Forever quest cache also holds a level and a
minimum level per quest (`wfj.io.wdb`, offsets 8 and 16), the source for the `assente` quests once a cache
is at hand; it is not read here.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from wfj.io.lua_reader import Table, as_int_id, parse_assignment
from wfj.paths import data_root

HEADER = "id\tmin\tlvl\tfonte"
ABSENT = "assente"


def _level(v: object) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def read_levels(pfquest_lua: Path) -> dict[int, tuple[int | None, int | None]]:
    """id → (min, lvl) from pfQuest's `pfDB["quests"]["data"]` table."""
    name, table = parse_assignment(Path(pfquest_lua).read_text(encoding="utf-8-sig"))
    if name != "pfDB":
        raise ValueError(f"unexpected table {name!r} (want pfDB[\"quests\"][\"data\"])")
    out: dict[int, tuple[int | None, int | None]] = {}
    for key, val in table.items:
        if isinstance(val, Table):
            out[as_int_id(key)] = (_level(val.get("min")), _level(val.get("lvl")))
    return out


def english_quest_ids(data: Path) -> set[int]:
    ids: set[int] = set()
    for path in sorted((Path(data) / "english" / "quest").glob("quest-*.jsonl")):
        with path.open(encoding="utf-8") as f:
            ids.update(json.loads(raw)["id"] for raw in f if raw.strip())
    return ids


def table_rows(levels: dict[int, tuple[int | None, int | None]], ids: set[int], commit: str) -> list[str]:
    def cell(v: int | None) -> str:
        return "" if v is None else str(v)

    rows = []
    for id_ in sorted(ids):
        if id_ in levels:
            mn, lvl = levels[id_]
            rows.append(f"{id_}\t{cell(mn)}\t{cell(lvl)}\tpfquest@{commit}")
        else:
            rows.append(f"{id_}\t\t\t{ABSENT}")
    return rows


def ids_up_to(level: int, table: Path) -> list[int]:
    """The quests whose own level (`lvl`) is at most `level`; `assente` quests are never included."""
    out = []
    for line in Path(table).read_text(encoding="utf-8").splitlines():
        if not line or line == HEADER or line.startswith("#"):
            continue
        id_, _mn, lvl, _src = line.split("\t")
        if lvl and int(lvl) <= level:
            out.append(int(id_))
    return sorted(out)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj.dev.quest_levels", description=__doc__.split("\n", 1)[0])
    p.add_argument("--pfquest", required=True, type=Path, help="pfQuest's db/quests.lua")
    p.add_argument("--commit", default="7786596", help="the pfQuest commit the file was fetched at")
    p.add_argument("--data", type=Path, help="the data/ folder (default: found above the current directory)")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    ids = english_quest_ids(a.data or data_root())
    rows = table_rows(read_levels(a.pfquest), ids, a.commit)
    a.out.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    absent = sum(r.endswith(f"\t{ABSENT}") for r in rows)
    print(f"quest levels: {len(rows)} quests, {absent} {ABSENT}; up to 20: {len(ids_up_to(20, a.out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
