"""Player tokens in the Italian corpus. Pure.

The human quest corpus keeps the predecessor's tokens literally in `it`; the addon expands them when the
Italian is applied (`Core/Placeholders.lua`). Tokens stay literal in `data/`. This module is the pipeline's
view of the same vocabulary: what counts as a token, which ones the addon knows, and which are unknown
(validate).

- `{word}`: `name`, `class`, `race` are known; anything else between braces (`{foo}`, `{name1}`, `{ name }`,
  `{名前}`) is unknown: the addon leaves it literal
- `<a/b>`: a gender word pair, expanded by the player's sex (`<il/la>`, `<caro/cara>`, `<è/é>`): two runs of
  Unicode letters, accented ones included. The addon's twin takes ASCII letters or any UTF-8 byte (≥ 0x80), so
  it also expands a pair with a non-ASCII mark (`<a…/b>`) that this module calls unknown: validate refuses
  such a line, so the wider runtime class never meets one. Any other `<x/y>` pair (`<Mr./Ms.>`, `<1/2>`) is
  not expanded and would show both forms
- `PLACEHOLDER_NAMES`: the Italian class / race words by token, (male, female), that `wfj generate` writes to
  `Data/Placeholders.lua` (`WFJ.PlaceholderNames`). Read from `pipeline/placeholder_names.tsv`, which
  `wfj import official` writes from the retail itIT `ChrClasses` (`Name_male_lang`, `Name_female_lang`) and
  `ChrRaces` (`Name_lang`, `Name_female_lang`) tables: Blizzard's own forms, for the tokens in `TOKENS`
"""

from __future__ import annotations

import re
from pathlib import Path

KNOWN: tuple[str, ...] = ("name", "class", "race")
_BRACES = re.compile(r"\{([^{}\n]*)\}")
_PAIR = re.compile(r"<([^\W\d_]+)/([^\W\d_]+)>")
_ANY_PAIR = re.compile(r"<[^<>/\n]+/[^<>/\n]+>")


# The class and race tokens Forever's player can have (UnitClass / UnitRace's 2nd value): Classic's nine
# classes and eight races. Forever's ChrRaces lists no other playable race with an Italian name on retail
# (its Skyborne rows are `TBD NPC Race` there), so a race outside this list shows the client's own name.
TOKENS: dict[str, tuple[str, ...]] = {
    "CLASS": ("WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "SHAMAN", "MAGE", "WARLOCK", "DRUID"),
    "RACE": ("Human", "Orc", "Dwarf", "NightElf", "Scourge", "Tauren", "Gnome", "Troll"),
}
NAMES_FILE = Path(__file__).resolve().parents[2] / "placeholder_names.tsv"
NAMES_HEADER = "# <kind> <token> <male> <female>, tab-separated, by `wfj import official` ({src}); no edits\n"


def parse_names(text: str) -> dict[str, dict[str, tuple[str, str]]]:
    """The names file: one tab-separated `<kind> <token> <male> <female>` line per token; `#` lines are
    comments."""
    out: dict[str, dict[str, tuple[str, str]]] = {}
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) != 4 or not all(p.strip() for p in parts):
            raise ValueError(f"placeholder names:{n}: not four tab-separated fields: {raw!r}")
        kind, token, male, female = parts
        if token in out.setdefault(kind, {}):
            raise ValueError(f"placeholder names:{n}: {kind} {token} listed twice")
        out[kind][token] = (male, female)
    return out


def names_text(names: dict[str, dict[str, tuple[str, str]]], src: str) -> str:
    rows = [f"{k}\t{t}\t{m}\t{f}\n" for k in sorted(names) for t, (m, f) in sorted(names[k].items())]
    return NAMES_HEADER.format(src=src) + "".join(rows)


def read_names(path: Path) -> dict[str, dict[str, tuple[str, str]]]:
    return parse_names(Path(path).read_text(encoding="utf-8"))


PLACEHOLDER_NAMES: dict[str, dict[str, tuple[str, str]]] = read_names(NAMES_FILE)


def split_pairs(it: str | None) -> list[tuple[str, str]]:
    """Every gender pair in `it` as (male, female), in reading order: `<è/é>` → [("è", "é")]."""
    return _PAIR.findall(it or "")


def tokens(it: str | None) -> list[str]:
    """Every token in `it`, as a display key: `{name}`, `{foo}` … or `<a/b>` for a gender pair."""
    it = it or ""
    return [f"{{{w}}}" for w in _BRACES.findall(it)] + ["<a/b>"] * len(_PAIR.findall(it))


def unknown(it: str | None) -> list[str]:
    """What the addon would render literally: brace tokens outside KNOWN, and `<x/y>` pairs it cannot
    expand."""
    it = it or ""
    bad = [f"{{{w}}}" for w in _BRACES.findall(it) if w not in KNOWN]
    bad += [m for m in _ANY_PAIR.findall(it) if not _PAIR.fullmatch(m)]
    return bad
