"""The retail client tables in both locales (`make wago-fetch-retail`): `<table>.enUS.csv` and
`<table>.itIT.csv` in one folder, stamped `wago@<build>` per locale file (io/tables_stamp).

wago.tools serves Italian text only for the retail client, so Blizzard's own Italian comes from there: each
reader of io/wago reads both files of a table the same way, and `wfj import official` keeps a row only where
the retail English is the English Forever shows.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, TypeVar

from wfj.io.wago import (  # noqa: F401  (re-exported: the readers callers pair)
    read_global_strings,
    read_item_descriptions,
    read_spell_texts,
    read_subtexts,
)

LOCALES = ("enUS", "itIT")
T = TypeVar("T")


def csv_path(folder: Path, table: str, locale: str) -> Path:
    return Path(folder) / f"{table}.{locale}.csv"


def files(folder: Path, tables: Iterable[str]) -> list[Path]:
    """Both locale files of every table, in a stable order (what the stamp check is given)."""
    return [csv_path(folder, t, loc) for t in tables for loc in LOCALES]


def read_pair(folder: Path, table: str, reader: Callable[[Path], T]) -> tuple[T, T]:
    """(enUS, itIT) of one table, each read by `reader` (an io/wago reader)."""
    return reader(csv_path(folder, table, "enUS")), reader(csv_path(folder, table, "itIT"))


def _rows(path: Path, need: tuple[str, ...]) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in need if reader.fieldnames is None or c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{Path(path).name}: need columns {list(need)}, have {reader.fieldnames}")
        return list(reader)


def read_placeholder_names(
    folder: Path, tokens: dict[str, tuple[str, ...]]
) -> tuple[dict[str, dict[str, tuple[str, str]]], list[str]]:
    """Blizzard's Italian class and race words by token, (male, female), for the tokens in `tokens`:
    ChrClasses by `Filename` (`Name_male_lang`, else `Name_lang`; `Name_female_lang`), ChrRaces by
    `ClientFileString` (`Name_lang`; `Name_female_lang`). A row with no female form takes the male one; a
    token on several rows (`Human`: Human, Gilnean) takes the lowest id's.
    → (names, the tokens no row names)."""
    sources = {
        "CLASS": ("ChrClasses", "Filename", ("Name_male_lang", "Name_lang"), "Name_female_lang"),
        "RACE": ("ChrRaces", "ClientFileString", ("Name_lang",), "Name_female_lang"),
    }
    names: dict[str, dict[str, tuple[str, str]]] = {}
    absent: list[str] = []
    for kind, (table, token_col, male_cols, female_col) in sources.items():
        rows = _rows(csv_path(folder, table, "itIT"), ("ID", token_col, male_cols[-1], female_col))
        by_token: dict[str, tuple[int, str, str]] = {}
        for row in rows:
            token = (row[token_col] or "").strip()
            male = next((row[c].strip() for c in male_cols if (row.get(c) or "").strip()), "")
            if token not in tokens[kind] or not male:
                continue
            female = (row[female_col] or "").strip() or male
            rid = int(row["ID"])
            if token not in by_token or rid < by_token[token][0]:
                by_token[token] = (rid, male, female)
        names[kind] = {t: (m, f) for t, (_, m, f) in sorted(by_token.items())}
        absent += [f"{kind} {t}" for t in tokens[kind] if t not in by_token]
    return names, absent
