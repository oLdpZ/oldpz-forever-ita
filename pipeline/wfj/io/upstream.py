"""Read the English rows of the Japanese project's clone (`data/english/<type>/<type>-*.jsonl`).

Only the English is read, never a translation file. The rows share our schema (`id, field, en, hash, src`,
`npcs` for gossip); what to keep is decided by `cmd/import_english.run_upstream`."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from wfj.io.wdb import PLACEHOLDER_TITLE

# a stand-in the project left in a quest's text: the whole quest is unusable
PLACEHOLDER_TEXT = re.compile(r"temp text|<CHANGE TO GOSSIP>|^\s*TEST\b", re.IGNORECASE)


def head_commit(clone: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def read_english(clone: Path, type_: str) -> list[dict[str, Any]]:
    d = Path(clone) / "data" / "english" / type_
    rows: list[dict[str, Any]] = []
    for path in sorted(d.glob(f"{type_}-*.jsonl")):
        with path.open(encoding="utf-8") as f:
            rows.extend(json.loads(raw) for raw in f if raw.strip())
    return rows


def placeholder_quest_ids(lines: list[dict[str, Any]]) -> set[int]:
    """Quests whose title is a stand-in or any of whose fields holds placeholder text."""
    bad: set[int] = set()
    for ln in lines:
        en = ln.get("en") or ""
        if (ln.get("field") == "title" and PLACEHOLDER_TITLE.match(en)) or PLACEHOLDER_TEXT.search(en):
            bad.add(ln["id"])
    return bad
