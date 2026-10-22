"""The dialogue priority table: which `gossip` lines a level 1-20 player meets first, so lots go in order.

    python -m wfj.dev.gossip_priority --db <mangos.sqlite> [--data <data/>] [--levels quest_levels.tsv] \
        --out gossip_priority.tsv

Gossip lines carry no zone, only the hash of their English, so the VMaNGOS database says who speaks them.
Tier 1: lines of the NPCs that give or end a quest of level 20 or less, and every dialogue option. Tier 2:
lines of NPCs reaching level 30 at most (starting zones, low capitals). Tier 3: lines of every other NPC with
a menu or a greeting. Tier 4: the rest of the store (chat, yells, emotes, other sources). A hash keeps the
lowest tier it appears in. The database may be newer than the English pin: its hashes missing from the store
are dropped and counted. Output: `id<TAB>livello`, sorted by tier then hash.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from wfj.core.hashing import key as hash_key
from wfj.core.normalize import normalize_v1
from wfj.dev.quest_levels import ids_up_to
from wfj.io import vmangos
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

HEADER = "id\tlivello"
QUEST_LEVEL = 20
NPC_LEVEL = 30


def _hash(en: str) -> str | None:
    norm = normalize_v1(en)
    return hash_key(norm) if norm else None


def classify(db: Path, data: Path, levels: Path) -> tuple[list[tuple[str, int]], int]:
    """((hash, tier) for every store hash, sorted by tier then hash; database hashes the store lacks)."""
    store = {ln["id"] for ln in Store(data, english=True).load("gossip")}
    quests = set(ids_up_to(QUEST_LEVEL, levels))
    starters, _objects, enders = vmangos.read_quest_speakers(db, quests)
    givers = {c for ids in (*starters.values(), *enders.values()) for c in ids}
    max_level = vmangos.read_creature_max_levels(db)
    low = {c for c, lv in max_level.items() if lv <= NPC_LEVEL}
    tier: dict[str, int] = {}
    seen: set[str] = set()

    def put(en: str, t: int) -> None:
        k = _hash(en)
        if k is None:
            return
        seen.add(k)
        tier[k] = min(t, tier.get(k, t))

    for en in vmangos.read_gossip_options(db):
        put(en, 1)
    # one pass over every speaking creature: its tier by who it is
    for creature, en in vmangos.read_creature_lines(db, vmangos.read_gossip_creatures(db)):
        put(en, 1 if creature in givers else 2 if creature in low else 3)
    rows = sorted(((k, tier.get(k, 4)) for k in store), key=lambda r: (r[1], r[0]))
    return rows, len(seen - store)


def build(db: Path, data: Path, levels: Path) -> list[tuple[str, int]]:
    return classify(db, data, levels)[0]


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj.dev.gossip_priority", description=__doc__.split("\n", 1)[0])
    p.add_argument("--db", required=True, type=Path, help="the VMaNGOS mangos.sqlite")
    p.add_argument("--data", type=Path, help="the data/ folder (default: found above the current directory)")
    p.add_argument("--levels", type=Path, default=Path("quest_levels.tsv"))
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    rows, dropped = classify(a.db, a.data or data_root(), a.levels)
    a.out.write_text("\n".join([HEADER, *(f"{h}\t{t}" for h, t in rows)]) + "\n", encoding="utf-8")
    counts = Counter(t for _h, t in rows)
    print("gossip priority: " + ", ".join(f"tier {t}: {counts[t]}" for t in (1, 2, 3, 4))
          + f"; {dropped} database hashes missing from the store (dropped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
