"""The voice packs the whole game is split into: a committed table (`pipeline/voice-packs.toml`) of quest
level bands plus one pack for the rest. Pure: the table and the level file are read as text.

A line's pack depends only on that line: a quest field (`<quest id>-<field>`) goes to the band of its quest's
own level (`lvl` of `pipeline/quest_levels.tsv`, its `min` when `lvl` is empty); a book page (`b-…`), a
gossip line (`g-…`) and a quest with no known level go to the pack marked `other`. So a fix to one line
re-releases one pack. A level under the first band goes to the first, over the last band to the last.

Each pack's folder is `OldpZ_ForeverITA_Voce_<suffix>`: the addon accepts any folder that starts with
`OldpZ_ForeverITA_Voce` and is made only of letters, digits and `_` (`^[%w_]+$`, Core/Voice.lua), so a
suffix never holds `-`.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

BASE = "OldpZ_ForeverITA_Voce"
SUFFIX = re.compile(r"^[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*$")
QUEST_KEY = re.compile(r"^(\d+)-[a-z]+$")


@dataclass(frozen=True)
class Pack:
    """One pack: its folder suffix, the words its title adds, and the quest levels it holds (inclusive), or
    `other` for books, gossip and quests with no known level."""

    suffix: str
    title: str
    levels: tuple[int, int] | None = None

    @property
    def folder(self) -> str:
        return f"{BASE}_{self.suffix}"

    @property
    def other(self) -> bool:
        return self.levels is None


def parse_packs(text: str, source: str = "voice-packs.toml") -> list[Pack]:
    """The table's packs, in order. Refused (ValueError naming `source`): a suffix the addon would refuse or
    seen twice, an empty title, a band that is not `[low, high]` with 1 <= low <= high, bands that overlap or
    leave a gap, no band, or not exactly one `other` pack."""
    rows = tomllib.loads(text).get("pack")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{source}: no [[pack]]")
    out: list[Pack] = []
    for n, row in enumerate(rows, 1):
        suffix, title = row.get("suffix"), row.get("title")
        if not isinstance(suffix, str) or not SUFFIX.match(suffix):
            raise ValueError(f"{source}: pack {n}: suffix {suffix!r} is not letters, digits and single '_'")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{source}: pack {suffix}: no title")
        levels, other = row.get("levels"), row.get("other", False)
        if other is True and levels is None:
            out.append(Pack(suffix, title))
            continue
        if other or not (isinstance(levels, list) and len(levels) == 2
                         and all(isinstance(v, int) and not isinstance(v, bool) for v in levels)
                         and 1 <= levels[0] <= levels[1]):
            raise ValueError(f"{source}: pack {suffix}: want levels = [low, high] or other = true")
        out.append(Pack(suffix, title, (levels[0], levels[1])))
    if len({p.suffix.lower() for p in out}) != len(out):
        raise ValueError(f"{source}: a suffix is used twice")
    if sum(p.other for p in out) != 1:
        raise ValueError(f"{source}: want exactly one pack with other = true")
    bands = sorted(p.levels for p in out if p.levels is not None)
    if not bands:
        raise ValueError(f"{source}: no level band")
    for (_, hi), (lo, _) in zip(bands, bands[1:], strict=False):
        if lo != hi + 1:
            raise ValueError(f"{source}: the bands must follow each other, no gap or overlap ({hi}, {lo})")
    return out


def parse_levels(text: str) -> dict[int, int]:
    """{quest id: level} from quest_levels.tsv (id, min, lvl, fonte): `lvl`, else `min`; a quest with
    neither (`assente`) is left out."""
    out: dict[int, int] = {}
    for raw in text.splitlines():
        if not raw.strip() or raw.startswith(("#", "id\t")):
            continue
        id_, mn, lvl, *_ = raw.split("\t")
        level = lvl or mn
        if level:
            out[int(id_)] = int(level)
    return out


def level_of(key: str, levels: Mapping[int, int]) -> int | None:
    """The level of a line's quest; None for a book page, a gossip line or a quest with no known level."""
    m = QUEST_KEY.match(key)
    return levels.get(int(m.group(1))) if m else None


def pack_of(key: str, packs: Sequence[Pack], levels: Mapping[int, int]) -> Pack:
    """The pack a line goes to (see the module's doc)."""
    level = level_of(key, levels)
    bands = sorted((p for p in packs if p.levels is not None), key=lambda p: p.levels or (0, 0))
    if level is None:
        return next(p for p in packs if p.other)
    for p in bands:
        assert p.levels is not None
        if level <= p.levels[1]:
            return p
    return bands[-1]


def find(packs: Sequence[Pack], name: str) -> Pack:
    """A pack by its suffix or its folder name (any case)."""
    for p in packs:
        if name.lower() in (p.suffix.lower(), p.folder.lower()):
            return p
    raise ValueError(f"no voice pack {name!r}: {', '.join(p.suffix for p in packs)} or all")
