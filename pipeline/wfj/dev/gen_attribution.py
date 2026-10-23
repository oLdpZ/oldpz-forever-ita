"""Generate ATTRIBUTION.md: the upstream code this fork is built on, every translator whose Italian is in
`data/`, and the notices the English sources came with.

Usage: python -m wfj.dev.gen_attribution [--out ATTRIBUTION.md] [--data DIR]

The translator list is the union of the tags on the hand-written lines in `data/` (shipped or not, since the
repository publishes both) and the tags the file already lists, so a credit is never dropped. The output is
committed; tests/python/test_attribution.py fails when `data/` holds a translator the file does not list.

No Japanese text ships: the upstream project's Japanese translations and their translators' credits stayed
upstream when the store was emptied (Plan 1, Task 7).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from wfj.core import decisions, fix_report
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

UPSTREAM = """\
## Upstream code

oLd_pZ Forever - Traduzione Italiana is a fork of **WoW Forever Japanese** by **Zyaga**
(https://github.com/zyaga/wow-forever-japanese), released under GPL-2.0-or-later, taken at commit
`1578af4b5bffffbe3d89d729ef769e068511d425` (1578af4b). Its addon architecture, data pipeline, tests and
documentation are reused and modified here under the same license. Its Japanese translations are not part of
this project: no Japanese text ships. This credit claims no support from the upstream author.
"""

LINEAGE = """\
## Lineage

WoW Forever Japanese's addon code descends, as its own credits state, from these earlier addons (GPLv2,
CurseForge):

1. **WoWpoPolsku-Quests** (Platine, wowpopolsku.pl): the addon architecture the later forks used.
2. **Classic Quest Chinese Translator** (luckycat_tv) and **Tooltips Translator - Chinese** (qqytqqyt).
3. **Classic Quest Japanese Translator** (Crynok / Zyaga) and **Classic Tooltip Japanese Translator** (Zyaga):
   addons for WoW Classic.

## English source text

The English text in `data/english/` is Blizzard Entertainment's. It is kept to align and hash the
translations and is never shipped in the addon. It was read from the Forever client's own tables and quest
cache, the Classic Era quest cache, wago.tools DB2 exports (`ItemSparse`, `SpellName`), and:

- pfQuest (`db/enUS/quests.lua`, https://github.com/shagu/pfQuest), under the MIT License (below);
- the VMaNGOS world database (https://github.com/vmangos/core, release `db_latest`, snapshot `db-13b49dc`),
  GPL-2.0: quest progress and completion text, gossip and book pages.
<FOREVER_VO_SOURCE>
## pfQuest license

> MIT License
>
> Copyright (c) 2017-2021 Eric Mauser (Shagu)
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
> following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial
> portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
> LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
> EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
> AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
> OR OTHER DEALINGS IN THE SOFTWARE.
<FOREVER_VO_LICENSE>
## This project

oLd_pZ Forever - Traduzione Italiana ships its own code and translations under GPL-2.0-or-later (see
`LICENSE`); every translated line keeps its provenance in `data/` (`provenance.translator`, or the model that
drafted it). The English text in `data/english/` is Blizzard Entertainment's and is not licensed by this
project. Details: `docs/legal/licensing.md`.
"""

# forever-vo's credit is written only while some English line still comes from it (ADR-055): once another
# source has replaced every one, a regeneration drops the credit with them.
FOREVER_VO = "forever-vo"
FOREVER_VO_SOURCE = """\
- forever-vo (https://github.com/quinn-dougherty/forever-vo), under the MIT License (below): quest progress
  and turn-in text and NPC greetings that players of the Forever client recorded with its addon and sent in.
"""
FOREVER_VO_LICENSE = """
## forever-vo license

> MIT License
>
> Copyright (c) 2026 Quinn Dougherty
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
> following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial
> portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
> LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
> EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
> AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
> OR OTHER DEALINGS IN THE SOFTWARE.
"""
NO_TRANSLATORS = "No hand-written Italian translation ships yet."
OFFICIAL = """## Blizzard's Italian text

Most of the Italian this addon ships is not a translation of ours. It is the work of
Blizzard Entertainment (testi ufficiali itIT): the Italian of the retail World of Warcraft client,
read from its client tables (GlobalStrings, Faction, ItemSparse, Spell, ChrClasses, ChrRaces) through
wago.tools DB2 exports, and kept only where the retail English is the English Forever shows
(`wfj import official`). Its lines carry the provenance class `official`. Retail builds read: <BUILDS>.
"""
WOWHEAD = "wowhead"
WOWHEAD_NAMES = """
NPC names the client tables lack are Blizzard's Italian as Wowhead's Italian tooltips show it
(`make creature-official`, ADR-103): only the creature id and its name, read on <DATES>.
"""


def english_sources(root: Path) -> set[str]:
    """The source names (`src` before the `@`) of every line in `data/english/`."""
    names: set[str] = set()
    for path in sorted((root / "english").glob("*/*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                names.add(str(json.loads(raw)["src"]).split("@", 1)[0])
    return names


_LISTED = re.compile(r"^- (.+)$", re.M)
_TRANSLATORS = re.compile(r"^## Translators.*?(?=^## |\Z)", re.M | re.S)


def _sorted(tags: set[str]) -> list[str]:
    tags.discard("")
    return sorted(tags, key=lambda t: (t.casefold(), t))


def data_translators(root: Path) -> list[str]:
    """The translator of every hand-written variant in `data/` but Blizzard's, the line's own and its
    `conflicts`. A player credited through a fix report is left to the Correctors section."""
    tags: set[str] = set()
    store = Store(root)
    for type_ in fix_report.TYPES:
        for line in store.load(type_):
            for v in decisions.hand_written_variants(line):
                prov = v["provenance"]
                # Blizzard's own Italian (`official`) names no translator: the README credits its source
                if "report" not in prov and not decisions.is_official(prov):
                    tags.add(prov["translator"])
    return _sorted(tags)


def official_sources(root: Path) -> list[str]:
    """The `source` of every official (Blizzard itIT) variant in `data/` (`wago-itit@<build>`), sorted."""
    found: set[str] = set()
    store = Store(root)
    for type_ in fix_report.TYPES:
        for line in store.load(type_):
            for v in decisions.variant_dicts(line):
                if decisions.is_official(v["provenance"]):
                    found.add(str(v["provenance"]["source"]))
    return sorted(found)


def listed_translators(text: str) -> list[str]:
    """The tags an ATTRIBUTION.md already lists under Translators."""
    m = _TRANSLATORS.search(text)
    return _sorted(set(_LISTED.findall(m.group(0)))) if m else []


CORRECTORS = "## Correctors"
_SECTION = re.compile(r"^## Correctors.*?(?=^## )", re.M | re.S)


def correctors_section(entries: dict[str, list[int]]) -> str:
    """The players (ADR-045) whose own Italian a fix report brought in, with their report (issue)
    numbers; empty when there are none."""
    if not entries:
        return ""
    lines = [f"{CORRECTORS} (players whose fixes ship, with their fix reports)", ""]
    for name in sorted(entries, key=lambda t: (t.casefold(), t)):
        lines.append(f"- {name}: " + ", ".join(f"#{n}" for n in entries[name]))
    return "\n".join(lines) + "\n\n"


def with_correctors(text: str, entries: dict[str, list[int]]) -> str:
    """`text` with its Correctors section (before Lineage) set to `entries`; every other section unchanged."""
    text = _SECTION.sub("", text)
    at = text.find("## Lineage")
    section = correctors_section(entries)
    if not section or at < 0:
        return text
    return text[:at] + section + text[at:]


def render(
    tags: list[str], sources: set[str] | frozenset[str] = frozenset(), official: set[str] | list[str] = ()
) -> str:
    """The whole file. `sources`: the English source names in `data/english/` (english_sources);
    `official`: the official variants' sources (official_sources), credited to Blizzard when there are any."""
    tags = _sorted(set(tags))
    lines = ["# Attribution", "", UPSTREAM.rstrip("\n"), ""]
    lines += [f"## Translators ({len(tags)} tags, as recorded in data/)", ""]
    lines += [f"- {t}" for t in tags] or [NO_TRANSLATORS]
    vo = FOREVER_VO in sources
    lineage = LINEAGE.replace("<FOREVER_VO_SOURCE>\n", (FOREVER_VO_SOURCE if vo else "") + "\n")
    lineage = lineage.replace("<FOREVER_VO_LICENSE>\n", (FOREVER_VO_LICENSE if vo else "") + "\n")
    if official:
        # after Lineage, beside the English source credit: the part above Lineage never reads "official"
        # (no claim that the project is Blizzard's; test_public_docs)
        # Wowhead's NPC names (ADR-103) are dated reads, not retail builds: credited apart
        wowhead = sorted(s.split("@", 1)[-1] for s in set(official) if s.startswith(WOWHEAD + "@"))
        tables = sorted(s for s in set(official) if not s.startswith(WOWHEAD + "@"))
        builds = ", ".join(f"`{s.split('@', 1)[-1]}`" for s in tables)
        text = OFFICIAL.replace("<BUILDS>", builds or "none")
        if wowhead:
            text += WOWHEAD_NAMES.replace("<DATES>", ", ".join(f"`{d}`" for d in wowhead))
        at = lineage.index("## This project")
        lineage = lineage[:at] + text + "\n" + lineage[at:]
    lines += ["", lineage]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gen_attribution")
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[3] / "ATTRIBUTION.md")
    p.add_argument("--data", type=Path, default=None, help="the data/ folder (default: this repository's)")
    a = p.parse_args(argv)
    out = a.out
    before = out.read_text(encoding="utf-8") if out.is_file() else ""
    tags = set(data_translators(a.data or data_root())) | set(listed_translators(before))
    # the Correctors section is written by `wfj report apply` from data/; a regeneration keeps it
    kept = _SECTION.search(before)
    data = a.data or data_root()
    text = render(_sorted(tags), english_sources(data), official_sources(data))
    if kept:
        at = text.find("## Lineage")
        # render always writes Lineage; without it the kept section goes at the end rather than being lost
        if at >= 0:
            text = text[:at] + kept.group(0) + text[at:]
        else:
            text = text.rstrip("\n") + "\n\n" + kept.group(0)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
