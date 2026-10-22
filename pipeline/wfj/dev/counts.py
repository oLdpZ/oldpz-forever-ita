"""How much ships in Italian, as the README and the CurseForge description show it.

`make coverage` writes these counts into README.md and docs/curseforge.md, in Italian, and
tests/python/test_counts.py fails when either is out of date. Quests, NPC lines, items, spells and UI are
the counts the generated Data/Meta.lua carries (the same numbers the settings page shows); book pages are
split into book and letter pages by pipeline/letter_pages.txt.
"""

from __future__ import annotations

import re
from pathlib import Path

from wfj.dev.letter_pages import read as read_letter_pages
from wfj.emit.lua_writer import keyed_rows
from wfj.io.jsonl_store import Store

META = Path("addon/OldpZ_ForeverITA/Data/Meta.lua")
LETTER_PAGES = Path("pipeline/letter_pages.txt")
README = Path("README.md")
CURSEFORGE = Path("docs/curseforge.md")

# (key, the README table's label, the CurseForge line's words after the number)
ROWS = (
    ("quest", "Missioni", "missioni"),
    ("gossip", "Righe di dialogo dei PNG", "righe di dialogo dei PNG"),
    ("book", "Pagine di libri", "pagine di libri"),
    ("letter", "Pagine di lettere", "pagine di lettere"),
    ("item", "Tooltip degli oggetti", "tooltip degli oggetti"),
    ("spell", "Tooltip delle abilità", "tooltip delle abilità"),
    ("ui", "Testi dell'interfaccia", "testi dell'interfaccia"),
)
README_HEADING = "## Cosa traduce"
CURSEFORGE_PREFIX = "In numeri: "

_COUNTS = re.compile(r"counts = \{([^}]*)\}")


def measure(repo: Path) -> dict[str, int]:
    match = _COUNTS.search((repo / META).read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"{META}: no counts table")
    meta = {k.strip(): int(v) for k, v in (p.split("=") for p in match.group(1).split(","))}
    # book pages ship keyed by their English, so count shipped keys as Meta.lua does (a page text two
    # pages share is one key); a key any letter page uses is a letter page
    letter_ids = read_letter_pages(repo / LETTER_PAGES)
    lines = [ln for ln in Store(repo / "data").load("book") if ln["id"] in letter_ids]
    letters = len(keyed_rows("book", lines))
    out = {k: meta[k] for k in ("quest", "gossip", "item", "spell", "ui")}
    out["book"] = meta["book"] - letters
    out["letter"] = letters
    return out


def _n(v: int) -> str:
    return f"{v:,}".replace(",", ".")  # the Italian thousands separator


def readme_table(c: dict[str, int]) -> str:
    return "| | In italiano |\n|---|---|\n" + "".join(f"| {label} | {_n(c[k])} |\n" for k, label, _ in ROWS)


def curseforge_line(c: dict[str, int]) -> str:
    return CURSEFORGE_PREFIX + ", ".join(f"**{_n(c[k])}** {words}" for k, _, words in ROWS) + "."


def _table_after(text: str, heading: str, table: str) -> str:
    start = text.index(heading + "\n\n") + len(heading) + 2
    end = text.index("\n\n", start) + 1
    return text[:start] + table + text[end:]


def _line(text: str, prefix: str, line: str) -> str:
    return re.sub(rf"^{re.escape(prefix)}.*$", lambda _: line, text, count=1, flags=re.M)


def apply_readme(text: str, c: dict[str, int]) -> str:
    return _table_after(text, README_HEADING, readme_table(c))


def apply_curseforge(text: str, c: dict[str, int]) -> str:
    return _line(text, CURSEFORGE_PREFIX, curseforge_line(c))


def write(repo: Path) -> list[Path]:
    """Rewrite the counts in README.md and docs/curseforge.md; the files that changed."""
    c = measure(repo)
    changed = []
    for rel, fn in ((README, apply_readme), (CURSEFORGE, apply_curseforge)):
        path = repo / rel
        old = path.read_text(encoding="utf-8")
        new = fn(old, c)
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
    return changed
