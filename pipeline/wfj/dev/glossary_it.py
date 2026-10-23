"""The official EN→IT glossary: Blizzard's Italian names, for the drafts of Plan 2.

    python -m wfj.dev.glossary_it --retail <retail folder> --build 12.1.5.70448 \
        --forever <Forever names folder> --forever-build 1.60.1.70532 [--out pipeline/glossario_ufficiale.tsv]

`pipeline/glossario_ufficiale.tsv` (`tipo\\tid\\ten\\tit`) lists, by kind:

- `zona` (AreaTable `AreaName_lang`), `fazione` (Faction `Name_lang`), `classe` (ChrClasses, the male and
  the female form, one row each) and `razza` (ChrRaces, both forms): compared with Forever's own table of the
  same name (`<table>.csv` in the `--forever` folder, `make wago-fetch-forever-names`);
- `oggetto` (ItemSparse `Display_lang`) and `abilita` (SpellName `Name_lang`): compared with the item / spell
  names in data/english.
- `creatura` (NPC names): the `name` rows of `pipeline/creature_official.tsv` (`make creature-official`,
  Creature.db2 or Wowhead, already checked against data/english/unit), kept while their English is still the
  unit name in data/english. A one-word NPC name is kept only where the English corpus never writes the word
  in lower case (`Hogger` yes, `Imp` / `Wolf` no: `creature_terms`).

A row is kept only where the retail English for the id is Forever's English, the Italian differs from it, and
the name is no developer text (`wago.INTERNAL_TEXT`). A one-word item or spell name ("Charge", "Food",
"Shoot") is left out: it is an ordinary English word far more often than a name, and every quest line saying
it would carry a term the draft must not use. Zones, factions, classes and races keep their one-word names
(`Ironforge` → `Forgiardente`), except a zone or faction word the English corpus (data/english) writes in
lower case at least a fifth as often as capitalised (`Spirit`, `City`, `Red`, `Lighthouse`): a common word.

`pipeline/glossario_derivato.tsv` (`tipo\\tid\\ten\\tit\\tda`, hand-curated) adds the short forms quest text
uses for an official name (`Northshire` for `Northshire Valley` → `Contea del Nord`, `Crossroads` for `The
Crossroads`). `load_terms` reads it after the official glossary and refuses a row whose `da` is no official
term of that kind and id, or whose Italian is not part of that term's Italian; the builder checks it against
the glossary it has just written, so a rebuild that drops a term fails here.

`pipeline/glossario_curato.tsv` (`tipo\\ten\\tit\\tnota`, hand-curated) holds the names the coordinator
decided that neither file has (`Mage Quarter` → `Quartiere dei Maghi`, `SI:7` → `IR:7`, the tribes):
places, factions, organisations, peoples and tribes, never a common noun. Not Blizzard's, so `load_terms`
loads them as kind `curato` (id 0) after the others, and refuses one whose English an official or derived
term already has: they are marked like any name, but the lint only warns when a draft drops one.

`Matcher` finds the terms an English text holds: whole words, case-sensitive (a name is capitalised),
longest first and without overlap ("Stormwind City" → Roccavento, not the faction "Stormwind").
`translate_batch cut` attaches them to a row as `glossary` (`[en, it, kind]`); `translate_lint` reports
`glossary_term` when a draft carries none of a term's Italian forms: an error for a `zona`, `fazione`,
`classe` or `razza` name, a warning for an `oggetto`, `abilita` or (for now) `creatura` one.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from wfj.dev import creature_official
from wfj.io import retail, tables_stamp
from wfj.io.jsonl_store import Store
from wfj.io.wago import INTERNAL_TEXT

GLOSSARY = "glossario_ufficiale.tsv"
HEADER = "tipo\tid\ten\tit"
DERIVED = "glossario_derivato.tsv"
DERIVED_HEADER = "tipo\tid\ten\tit\tda"
CURATED = "glossario_curato.tsv"
CURATED_HEADER = "tipo\ten\tit\tnota"
CURATED_KIND = "curato"
# what a curated row may name (`tipo`): documentation for the reader, all loaded as CURATED_KIND
CURATED_TYPES = ("zona", "luogo", "fazione", "organizzazione", "popolo", "tribù")
GlossTerm = tuple[str, int, str, str]  # (kind, id, en, it)
KINDS = ("zona", "fazione", "classe", "razza", "oggetto", "abilita", "creatura")
CREATURE_KIND = "creatura"
# Matcher order (an (en, it) pair listed under two kinds keeps the first): an NPC name right after a zone,
# every official kind before a curated one
ORDER = ("zona", CREATURE_KIND, "fazione", "classe", "razza", "oggetto", "abilita", CURATED_KIND)
# kind → (table, English column, Italian columns: male first, then female when the kind has one)
TABLES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "zona": ("AreaTable", "AreaName_lang", ("AreaName_lang",)),
    "fazione": ("Faction", "Name_lang", ("Name_lang",)),
    "classe": ("ChrClasses", "Name_lang", ("Name_male_lang", "Name_female_lang", "Name_lang")),
    "razza": ("ChrRaces", "Name_lang", ("Name_lang", "Name_female_lang")),
    "oggetto": ("ItemSparse", "Display_lang", ("Display_lang",)),
    "abilita": ("SpellName", "Name_lang", ("Name_lang",)),
}
# the kinds whose Forever English is the data/english name line, by type
STORE_TYPES = {"oggetto": "item", "abilita": "spell", CREATURE_KIND: "unit"}
# `creatura` has no retail table here: its rows are pipeline/creature_official.tsv's `name` rows
CREATURES = "creature_official.tsv"
# the kinds whose one-word names are kept
ONE_WORD = frozenset({"zona", "fazione", "classe", "razza"})
WORD = re.compile(r"[A-Za-z0-9À-ÿ]+(?:['’\-][A-Za-z0-9À-ÿ]+)*")
MIN_LEN = 3
# a one-word zone / faction name is a common word when the corpus writes it lower case this often (×) or more
COMMON_RATIO = 5
COMMON_KINDS = frozenset({"zona", "fazione"})
# Not `unit`: an NPC name is a title-cased label (`Frenzy`, `Basilisk`), so it would count a common word as
# capitalised and turn it into a name (`Frenzy` → the faction "Piranha")
CORPUS_TYPES = ("quest", "gossip", "book", "objective", "area", "item", "spell", "ui")


def _column(path: Path, id_col: str, cols: Iterable[str]) -> dict[int, list[str]]:
    """{id: [the text of each column]} ("" for a column the table lacks or leaves empty)."""
    cols = list(cols)
    out: dict[int, list[str]] = {}
    with Path(path).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or id_col not in reader.fieldnames:
            raise ValueError(f"{Path(path).name}: no {id_col} column")
        for row in reader:
            out[int(row[id_col])] = [(row.get(c) or "").strip() for c in cols]
    return out


def _forever_english(kind: str, english: Store, forever: Path | None) -> dict[int, str] | None:
    if kind in STORE_TYPES:
        return {ln["id"]: ln["en"].strip() for ln in english.load(STORE_TYPES[kind]) if ln["field"] == "name"}
    if forever is None or not (Path(forever) / f"{TABLES[kind][0]}.csv").is_file():
        return None
    table, en_col, _ = TABLES[kind]
    return {i: v[0] for i, v in _column(Path(forever) / f"{table}.csv", "ID", [en_col]).items()}


def word_counts(english: Store) -> Counter[str]:
    """Every word of the English corpus, case kept."""
    counts: Counter[str] = Counter()
    for type_ in CORPUS_TYPES:
        for ln in english.load(type_):
            counts.update(WORD.findall(ln["en"]))
    return counts


def _usable(kind: str, en: str, it: str, counts: Counter[str]) -> bool:
    if not en or not it or it == en or len(en) < MIN_LEN or INTERNAL_TEXT.search(en):
        return False
    if any(c in en + it for c in "\t\n\r"):
        return False
    if len(WORD.findall(en)) >= 2:
        return True
    if kind in COMMON_KINDS and counts[en.lower()] * COMMON_RATIO >= max(counts[en], 1):
        return False
    return kind in ONE_WORD


def creature_terms(
    path: Path, forever: dict[int, str], counts: Counter[str]
) -> tuple[list[GlossTerm], list[str]]:
    """The `creatura` terms: the `name` rows of pipeline/creature_official.tsv whose English is still
    Forever's (`forever`, data/english/unit) and whose Italian differs. A one-word name is kept only where
    the English corpus never writes that word in lower case (`Hogger`): `Imp`, `Wolf`, `Defender` are also
    ordinary words, and every line saying "the imp" would carry a name the draft must not use. → (terms,
    the one-word names dropped)."""
    terms: list[GlossTerm] = []
    dropped: list[str] = []
    for id_, field, en, it, _ in creature_official.read_tsv(path):
        if field != "name" or forever.get(id_) != en:
            continue
        if not en or not it or it == en or len(en) < MIN_LEN or INTERNAL_TEXT.search(en):
            continue
        if any(c in en + it for c in "\t\n\r"):
            continue
        if len(WORD.findall(en)) < 2 and counts[en.lower()]:
            dropped.append(en)
            continue
        terms.append((CREATURE_KIND, id_, en, it))
    return terms, dropped


def unit_terms(data: Path, counts: Counter[str], conflicts: list[str] | None = None) -> list[GlossTerm]:
    """The NPC names of the `unit` table as `creatura` terms, for the marker pass (`dev.remark_names`): every
    trusted `name` row, official or machine, so a name drafted by a lot is the one the text shows too. The
    rules of `creature_terms` (a one-word name only where the corpus never writes it in lower case). One
    Italian per English: the official one, else the most common (then the first in Italian order); each
    English that had more than one is appended to `conflicts`. `data`: the data/ folder."""
    english = {ln["id"]: ln["en"].strip() for ln in Store(Path(data), english=True).load("unit")
               if ln["field"] == "name"}
    found: dict[str, list[tuple[bool, str, int]]] = {}
    for ln in Store(Path(data)).load("unit"):
        if ln["field"] != "name" or ln.get("status") != "trusted" or not isinstance(ln.get("it"), str):
            continue
        en, it = english.get(ln["id"]), ln["it"].strip()
        if not en or not it or it == en or len(en) < MIN_LEN or INTERNAL_TEXT.search(en):
            continue
        if any(c in en + it for c in "\t\n\r"):
            continue
        if len(WORD.findall(en)) < 2 and counts[en.lower()]:
            continue
        official = (ln.get("provenance") or {}).get("class") == "official"
        found.setdefault(en, []).append((official, it, ln["id"]))
    terms: list[GlossTerm] = []
    for en, rows in sorted(found.items()):
        tally = Counter(it for _, it, _ in rows)
        official = Counter(it for o, it, _ in rows if o)
        pool = official or tally
        it = sorted(pool, key=lambda f: (-pool[f], f))[0]
        if len(tally) > 1 and conflicts is not None:
            shown = ", ".join(f"{f} ×{n}" for f, n in sorted(tally.items()))
            conflicts.append(f"{en}: {shown} → {it}")
        terms.append((CREATURE_KIND, min(i for _, f, i in rows if f == it), en, it))
    return terms


def build_glossary(
    retail_dir: Path,
    english_store: Path,
    forever_dir: Path | None = None,
    creatures: Path | None = None,
    dropped: list[str] | None = None,
) -> list[GlossTerm]:
    """Every term of the glossary, sorted by kind (KINDS), id, Italian. `english_store` is data/english; a
    kind whose Forever table is not in `forever_dir` is left out (`missing_kinds` says which); `creatura`
    only with `creatures` (pipeline/creature_official.tsv), its one-word names left out appended to
    `dropped`."""
    english = Store(Path(english_store).parent, english=True)
    counts = word_counts(english)
    terms: set[GlossTerm] = set()
    for kind in KINDS:
        forever = _forever_english(kind, english, forever_dir)
        if forever is None:
            continue
        if kind == CREATURE_KIND:
            if creatures is not None:
                kept, left_out = creature_terms(creatures, forever, counts)
                terms.update(kept)
                if dropped is not None:
                    dropped += left_out
            continue
        table, en_col, it_cols = TABLES[kind]
        r_en = _column(retail.csv_path(retail_dir, table, "enUS"), "ID", [en_col])
        r_it = _column(retail.csv_path(retail_dir, table, "itIT"), "ID", it_cols)
        for id_, (en,) in r_en.items():
            if id_ not in r_it or forever.get(id_) != en:
                continue
            forms = r_it[id_]
            # ChrClasses: Name_male_lang, else Name_lang
            male = forms[0] or (forms[2] if kind == "classe" else "")
            female = forms[1] if len(forms) > 1 and forms[1] else male
            for it in dict.fromkeys([male, female]):
                if _usable(kind, en, it, counts):
                    terms.add((kind, id_, en, it))
    return sorted(terms, key=lambda t: (KINDS.index(t[0]), t[1], t[3]))


def missing_kinds(english_store: Path, forever_dir: Path | None) -> list[str]:
    english = Store(Path(english_store).parent, english=True)
    return [k for k in KINDS if _forever_english(k, english, forever_dir) is None]


def write_glossary(path: Path, terms: Iterable[GlossTerm]) -> None:
    rows = "".join(f"{k}\t{i}\t{en}\t{it}\n" for k, i, en, it in terms)
    Path(path).write_text(HEADER + "\n" + rows, encoding="utf-8")


def read_glossary(path: Path) -> list[GlossTerm]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != HEADER:
        raise ValueError(f"{path}: the first line must be {HEADER!r}")
    out: list[GlossTerm] = []
    for n, raw in enumerate(lines[1:], 2):
        parts = raw.split("\t")
        if len(parts) != 4 or parts[0] not in KINDS or not parts[1].isdigit():
            raise ValueError(f"{path}:{n}: not `tipo\\tid\\ten\\tit`: {raw!r}")
        out.append((parts[0], int(parts[1]), parts[2], parts[3]))
    return out


class Matcher:
    """The glossary terms an English text holds: whole words, case-sensitive, longest first, no overlap."""

    def __init__(self, terms: Iterable[GlossTerm]):
        self.forms: dict[str, list[str]] = {}
        # an (en, it) pair listed under two kinds keeps the first in KINDS order: a name kind before an item
        self.kinds: dict[tuple[str, str], str] = {}
        for kind, _, en, it in terms:
            forms = self.forms.setdefault(en, [])
            if it not in forms:
                forms.append(it)
            prior = self.kinds.get((en, it))
            if prior is None or ORDER.index(kind) < ORDER.index(prior):
                self.kinds[(en, it)] = kind
        self.by_first: dict[str, list[tuple[int, str]]] = {}
        for en in self.forms:
            words = WORD.findall(en)
            if words:
                self.by_first.setdefault(words[0], []).append((len(words), en))
        for cands in self.by_first.values():
            cands.sort(key=lambda c: (-c[0], -len(c[1])))

    def find(self, text: str) -> list[list[str]]:
        """[[en, it, kind], …] in reading order, each pair once (a class or race term gives both forms)."""
        words = list(WORD.finditer(text or ""))
        out: list[list[str]] = []
        i = 0
        while i < len(words):
            for n, en in self.by_first.get(words[i].group(), ()):
                if i + n <= len(words) and text[words[i].start() : words[i + n - 1].end()] == en:
                    out += [[en, it, self.kinds[(en, it)]] for it in self.forms[en]
                            if [en, it, self.kinds[(en, it)]] not in out]
                    i += n
                    break
            else:
                i += 1
        return out


def read_derived(path: Path) -> list[tuple[str, int, str, str, str]]:
    """`pipeline/glossario_derivato.tsv` (`tipo\\tid\\ten\\tit\\tda`): hand-curated short forms of official
    names (`Northshire` → `Contea del Nord`, from `Northshire Valley`). Shape only; `derived_terms` checks
    each row against the official glossary."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != DERIVED_HEADER:
        raise ValueError(f"{path}: the first line must be {DERIVED_HEADER!r}")
    out: list[tuple[str, int, str, str, str]] = []
    for n, raw in enumerate(lines[1:], 2):
        parts = raw.split("\t")
        if len(parts) != 5 or parts[0] not in KINDS or not parts[1].isdigit() or not all(parts[2:]):
            raise ValueError(f"{path}:{n}: not `tipo\\tid\\ten\\tit\\tda`: {raw!r}")
        out.append((parts[0], int(parts[1]), parts[2], parts[3], parts[4]))
    return out


def derived_terms(path: Path, official: Iterable[GlossTerm]) -> list[GlossTerm]:
    """The derived rows as glossary terms. Each must name an official term (`da`, with the same kind and id)
    and its Italian must be part of that term's Italian: a short form is cut from Blizzard's name, never
    invented."""
    by_key: dict[tuple[str, int, str], list[str]] = {}
    for kind, id_, en, it in official:
        by_key.setdefault((kind, id_, en), []).append(it)
    out: list[GlossTerm] = []
    for kind, id_, en, it, da in read_derived(path):
        forms = by_key.get((kind, id_, da))
        if forms is None:
            raise ValueError(f"{Path(path).name}: {en!r} derives from {kind} {id_} {da!r}, not in {GLOSSARY}")
        if not any(it in form for form in forms):
            official = " / ".join(forms)
            raise ValueError(f"{Path(path).name}: {en!r} → {it!r} is not part of {da!r} → {official}")
        out.append((kind, id_, en, it))
    return out


def curated_terms(path: Path, others: Iterable[GlossTerm]) -> list[GlossTerm]:
    """`pipeline/glossario_curato.tsv` (`tipo\\ten\\tit\\tnota`) as glossary terms of kind `curato`, id 0.
    A row must have a known `tipo` (CURATED_TYPES), an English and an Italian, and an English no official or
    derived term has (that one is Blizzard's, or derived from it)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != CURATED_HEADER:
        raise ValueError(f"{path}: the first line must be {CURATED_HEADER!r}")
    taken = {en for _, _, en, _ in others}
    out: list[GlossTerm] = []
    for n, raw in enumerate(lines[1:], 2):
        parts = raw.split("\t")
        if len(parts) != 4 or parts[0] not in CURATED_TYPES or not parts[1].strip() or not parts[2].strip():
            raise ValueError(f"{Path(path).name}:{n}: not `tipo\\ten\\tit\\tnota`: {raw!r}")
        if parts[1] in taken:
            raise ValueError(f"{Path(path).name}:{n}: {parts[1]!r} is already in {GLOSSARY} or {DERIVED}")
        out.append((CURATED_KIND, 0, parts[1], parts[2]))
    return out


def load_terms(repo: Path) -> list[GlossTerm]:
    """Every glossary term a draft is held to: the official glossary, then the derived short forms checked
    against it, then the curated names. The one loader for `cut`, the lint, `import draft` and `import
    official`."""
    official = read_glossary(Path(repo) / "pipeline" / GLOSSARY)
    derived = Path(repo) / "pipeline" / DERIVED
    terms = official + (derived_terms(derived, official) if derived.is_file() else [])
    curated = Path(repo) / "pipeline" / CURATED
    return terms + (curated_terms(curated, terms) if curated.is_file() else [])


def load_matcher(repo: Path) -> Matcher | None:
    """The committed glossary's matcher (official and derived terms), or None when the repository has no
    glossary."""
    path = Path(repo) / "pipeline" / GLOSSARY
    return Matcher(load_terms(repo)) if path.is_file() else None


def load_marker_matcher(repo: Path, conflicts: list[str] | None = None) -> Matcher | None:
    """`load_matcher` plus the `unit` table's NPC names (`unit_terms`, data/ in `repo`): the terms the marker
    pass (`dev.remark_names`) marks. A glossary term keeps its English: a unit name spelt like one is left
    out. Every other NPC name of several words (data/english/unit, no Italian yet) is a term of its own
    English: never marked (`names` skips a term whose two forms agree), it only keeps a shorter name inside
    it from being marked on its own (`Peddlefeet` in `Kwee Q. Peddlefeet`). None when the repository has no
    glossary."""
    path = Path(repo) / "pipeline" / GLOSSARY
    if not path.is_file():
        return None
    terms = load_terms(repo)
    taken = {en for _, _, en, _ in terms}
    data = Path(repo) / "data"
    english = Store(data, english=True)
    units = [t for t in unit_terms(data, word_counts(english), conflicts) if t[2] not in taken]
    taken |= {en for _, _, en, _ in units}
    whole = {ln["en"].strip(): ln["id"] for ln in english.load("unit") if ln["field"] == "name"}
    held = [(CREATURE_KIND, id_, en, en) for en, id_ in sorted(whole.items())
            if en not in taken and len(WORD.findall(en)) >= 2]
    return Matcher(terms + units + held)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="glossary_it", description=__doc__.split("\n\n")[0])
    ap.add_argument("--retail", type=Path, required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--forever", type=Path, required=True)
    ap.add_argument("--forever-build", required=True)
    ap.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[3] / "data")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / GLOSSARY)
    a = ap.parse_args(argv)
    try:
        tables = [t for t, _, _ in TABLES.values()]
        tables_stamp.check(retail.files(a.retail, tables), "wago", a.build)
        named = [a.forever / f"{TABLES[k][0]}.csv" for k in KINDS if k not in STORE_TYPES]
        tables_stamp.check(named, "wago", a.forever_build)
        creatures = a.out.with_name(CREATURES)
        one_word: list[str] = []
        terms = build_glossary(a.retail, a.data / "english", a.forever,
                               creatures if creatures.is_file() else None, one_word)
        derived_file = a.out.with_name(DERIVED)
        derived = derived_terms(derived_file, terms) if derived_file.is_file() else []
    except (OSError, ValueError) as e:
        print(f"glossary_it: {e}", file=sys.stderr)
        return 1
    write_glossary(a.out, terms)
    print(f"glossary_it: {len(derived)} derived terms checked ({DERIVED})")
    counts = {k: sum(1 for t in terms if t[0] == k) for k in KINDS}
    shown = ", ".join(f"{k} {n}" for k, n in counts.items())
    print(f"glossary_it: {len(terms)} terms → {a.out.name} ({shown})")
    if not creatures.is_file():
        print(f"glossary_it: no {CREATURES}: no creatura terms (make creature-official)")
    print(f"glossary_it: creatura: {len(one_word)} one-word names left out (lower case in the corpus)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
