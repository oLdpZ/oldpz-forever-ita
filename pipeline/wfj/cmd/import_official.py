"""wfj import official: Blizzard's own Italian from the retail itIT client tables (`make wago-fetch-retail`)
into data/ as `official` variants.

    wfj import official <retail folder> --build 12.1.5.70448 --date YYYY-MM-DD [--names PATH]

wago.tools serves Italian only for the retail client, whose text is years newer than Forever's. A retail row
is taken only where the retail English for the same id is the English Forever shows (the same hash, so the
same text after the English import's normalisation): an id alone says nothing, because retail rewords and
re-numbers. Then, per type:

- `ui` (GlobalStrings by key, `FactionDescription:<id>` from Faction, `SpellSubtext:<id>` from Spell): only
  the keys data/english/ui holds; the Italian must take exactly the English's format specifiers
  (`core/specifiers`, `rejected_specifiers`: `%d` for `%s` would break the client's `string.format`) and keep
  its colour codes and line breaks (`rejected_markup`).
- `item` `description` (ItemSparse `Description_lang`, the flavour text) and `spell` `description` / `aura`
  (Spell `Description_lang` / `AuraDescription_lang`): raw client templates. Each value code of the Italian
  is mapped to the English slot it names and written as the addon's placeholder, exactly as a draft writes
  it (`$s1` → `$N<k>`, `$d` → `$D<j>`; `convert_template`), and the result must pass the draft lint's rules
  (`translate_lint.check_row`). A code the Italian drops, adds or swaps is `rejected_slots`; a template with
  conditionals, inclusions or a name-list tail has no fixed slots and is `rejected_uncountable`. An item whose
  Forever English joins its Use / Equip spells before the flavour is not the flavour alone: a mismatch.
- `unit` `name` / `subname` (NPC names and titles): from `pipeline/creature_official.tsv` (`make
  creature-official`: Creature.db2 itIT, else the Wowhead tooltip), not the retail folder. A row is taken
  where its English is the data/english/unit English for that (id, field), as plain text; its source is
  `wago-itit@<build>` or `wowhead@<import date>`. A unit line is the name itself: never marked.

An accepted item / spell description gets the official glossary's names its English holds marked
`⟦en=it⟧` (spec §8, `core/names.mark_from_english`, the glossary beside data/ in pipeline/); UI text is
never marked.

Italian equal to the English (`same_as_english`) is not imported. The import owns every `official` variant:
one it no longer takes (the English changed, the retail text moved) is dropped, and a line left with no
variant goes. Lines are written `pending`; `wfj check` ranks `official` first (core/status.CLASS_RANK), and
a machine draft never replaces it without a ruling (`decisions.HAND_WRITTEN`).

It also writes the class / race words (`pipeline/placeholder_names.tsv`) from ChrClasses / ChrRaces, which
`wfj generate` turns into `Data/Placeholders.lua`.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from wfj.cmd import generate, validate
from wfj.core import align, decisions, language, markup, placeholders, specifiers
from wfj.core.hashing import key as hash_key
from wfj.core.model import entry, validate_line
from wfj.core.names import mark_from_english
from wfj.core.normalize import normalize_for
from wfj.dev import creature_official, glossary_it
from wfj.dev.translate_lint import check_row
from wfj.io import retail, tables_stamp, wago
from wfj.io.jsonl_store import Store

TYPES = ("ui", "item", "spell", "unit")
# unit: not from the retail folder but from `make creature-official` (Creature.db2 itIT, else Wowhead)
CREATURE_FILE = Path("pipeline") / creature_official.OUT.name
WOWHEAD = "wowhead"
TABLES = ("GlobalStrings", "ItemSparse", "Spell", "ChrClasses", "ChrRaces")
# Read when the folder has them: the UI text families whose table the retail fetch carries
FAMILY_TABLES = {"FactionDescription": "Faction"}
SOURCE = "wago-itit"
COUNTERS = (
    "accepted",
    "rejected_english_mismatch",
    "rejected_specifiers",
    "rejected_markup",
    "rejected_slots",
    "rejected_uncountable",
    "rejected_order",
    "rejected_ambiguous",
    "same_as_english",
    "no_italian",
)


@dataclasses.dataclass
class OfficialReport:
    """Per type: how many Forever English lines had a retail row, and what became of each."""

    counts: dict[str, Counter] = dataclasses.field(default_factory=lambda: {t: Counter() for t in TYPES})
    dropped: Counter = dataclasses.field(default_factory=Counter)  # official variants no longer taken
    absent_names: list[str] = dataclasses.field(default_factory=list)

    def render(self) -> str:
        rows = []
        for t in TYPES:
            c = self.counts[t]
            shown = " · ".join(f"{k} {c[k]}" for k in COUNTERS if c[k] or k == "accepted")
            rows.append(f"official {t}: {shown}")
        if self.dropped:
            shown = ", ".join(f"{t} {n}" for t, n in sorted(self.dropped.items()))
            rows.append(f"official variants dropped: {shown}")
        if self.absent_names:
            rows.append("placeholder names absent from the retail tables: " + ", ".join(self.absent_names))
        return "\n".join(rows)


def _hash(en: str) -> str:
    """The English import's hash of client-table text (`import_english._client_hash`)."""
    return hash_key(normalize_for("item", en))


def convert_template(en: str, it: str) -> tuple[str | None, str | None]:
    """Blizzard's Italian template `it` for the English template `en`, written with the addon's placeholders:
    each value code (`$s1`, `${…}`, `$1oa`) → `$N<k>`, k the English slot it names (reading order of `en`), a
    `$d` duration → `$D<j>`; a `$<n>w` counter is copied through and a literal stays a literal (the English
    must print the same ones). → (converted, None), or (None, reason): `uncountable` (no fixed slots:
    conditionals, inclusions, a name-list tail), `slots` (a code dropped, added, swapped or repeated, a
    literal changed, a word code the addon cannot expand, any rule of the draft lint) or `same_as_english`."""
    if align.UNCOUNTABLE.search(en) or align.UNCOUNTABLE.search(it) or align.split_tail(en)[1]:
        return None, "uncountable"
    slots = align.slots(en)
    if slots is None:
        return None, "uncountable"
    en_tokens = align.value_tokens(en)
    if len(en_tokens) != len(slots) or align.WORD_CODE.search(it):
        # a range ("$s1 to $s2") the addon reads as one value, or a `$l…;` / `$g…;` the addon cannot expand
        return None, "slots"
    codes: dict[str, list[str]] = {}
    literals: Counter = Counter()
    durations = 0
    for k, (m, slot) in enumerate(zip(en_tokens, slots, strict=True), 1):
        durations += slot.duration
        if m.lastgroup == "literal":
            literals[m.group()] += 1
        elif m.lastgroup == "counter":
            codes.setdefault(m.group(), []).append(m.group())
        else:
            codes.setdefault(m.group(), []).append(f"$D{durations}" if slot.client_unit else f"$N{k}")
    out, at = [], 0
    for m in align.value_tokens(it):
        if m.lastgroup == "literal":
            literals[m.group()] -= 1
            continue
        targets = codes.get(m.group())
        if not targets:
            return None, "slots"
        out += [it[at : m.start()], targets.pop(0)]
        at = m.end()
    if any(codes.values()) or any(literals.values()):
        return None, "slots"
    converted = "".join(out) + it[at:]
    # the paragraph count is a draft's rule (mirror the English's breaks); Blizzard's Italian sets its own,
    # and an old tooltip's two spaces after a full stop read as a break there
    reasons = [r for r in check_row({"en": en}, converted, set()) if not r.startswith("paragraphs:")]
    if reasons == ["not_italian"]:
        return None, "same_as_english"
    if reasons:
        return None, "slots"
    return converted, None


def _ui_verdict(en: str, it: str) -> tuple[str | None, str | None]:
    if not language.is_italian(it, en):
        return None, "same_as_english"
    if specifiers.mismatch(en, it):
        return None, "specifiers"
    if markup.mismatch(en, it):
        return None, "markup"
    return it, None


def _name_verdict(en: str, it: str) -> tuple[str | None, str | None]:
    """An NPC name or title: shipped as Blizzard wrote it, unless it reads as its English (`Imp`, `Ragnaros`:
    nothing to show, and `check` would reject it as not Italian)."""
    it = it.strip()
    if not language.is_italian(it, en.strip()):
        return None, "same_as_english"
    return it, None


_REASON = {
    "specifiers": "rejected_specifiers",
    "markup": "rejected_markup",
    "slots": "rejected_slots",
    "uncountable": "rejected_uncountable",
    "same_as_english": "same_as_english",
}


def settle_ui(
    taken: dict[tuple[Any, str], str], english: dict[str, str], addon_dir: Path | None, c: Counter
) -> list[tuple[str, str, str]]:
    """The UI rows the addon could not show as imported, dropped from `taken` (validate's `rule_ui`).

    - two free-text arguments the English separates only by a space, swapped in the Italian
      (`rejected_order`: the addon splits them lazily, so the values would land in each other's place);
    - keys whose English the addon's by-English index files together but whose Italian differs
      (`rejected_ambiguous`): none of them is kept, so the whole group stays English (one English, several
      Italian: `All` → `Tutto` / `Tutti`, the gender or number the English does not carry, would show the
      wrong agreement on some of them). A key that owns its Italian (UIStrings.OWN) is matched by name and
      never grouped.
    → the dropped ambiguous rows as (english, key, italian), sorted, for the review file (`ambiguous_text`).
    `addon_dir` None or missing: no declared argument kinds, chat families or owned keys."""
    kinds: dict[str, dict[int, str]] = {}
    chat: list[Any] = []
    own: set[str] = set()
    if addon_dir is not None and (addon_dir / "Core").is_dir():
        kinds, chat = validate.ui_arg_kinds(addon_dir), validate.ui_chat_families(addon_dir)
        own = validate.ui_own(addon_dir)
    groups: dict[str, list[tuple[Any, str]]] = {}
    for k in sorted(taken, key=lambda k: str(k[0])):
        en, it = english[k[0]], taken[k]
        if validate.adjacent_captures_reordered(en, it, validate.key_arg_kinds(k[0], kinds, chat)):
            del taken[k]
            c["accepted"] -= 1
            c["rejected_order"] += 1
            continue
        if k[0] in own:
            continue
        try:
            group, compared = validate.ui_group(k[0], en, it)
        except ValueError:  # a numbered row whose Italian does not fit its English
            del taken[k]
            c["accepted"] -= 1
            c["rejected_markup"] += 1
            continue
        groups.setdefault(group, []).append((k, compared))
    review: list[tuple[str, str, str]] = []
    for members in groups.values():
        if len({compared for _, compared in members}) < 2:
            continue
        for k, _ in members:
            review.append((english[k[0]], str(k[0]), taken.pop(k)))
            c["accepted"] -= 1
            c["rejected_ambiguous"] += 1
    return sorted(review)


AMBIGUOUS_FILE = Path(__file__).resolve().parents[2] / "ui_ambiguous.tsv"


def _tsv_cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def ambiguous_text(rows: list[tuple[str, str, str]]) -> str:
    """The review file: one row per key of each UI group `settle_ui` left English (english, key, italian;
    a backslash, tab or line break in a cell written `\\\\`, `\\t`, `\\n`). A ruling picks one Italian per
    English; until then the group ships no Italian."""
    out = ["english\tkey\titalian"]
    out += ["\t".join(_tsv_cell(cell) for cell in row) for row in rows]
    return "\n".join(out) + "\n"


def _retail_texts(folder: Path) -> dict[str, dict[tuple[Any, str], tuple[str, str]]]:
    """Per type: (id, field) → (retail English, retail Italian), every row present in both locales."""
    out: dict[str, dict[tuple[Any, str], tuple[str, str]]] = {t: {} for t in TYPES}

    def pair(type_: str, field: str, en: dict, it: dict) -> None:
        for k, text in en.items():
            if k in it:
                out[type_][(k, field)] = (text, it[k])

    g_en, g_it = retail.read_pair(folder, "GlobalStrings", retail.read_global_strings)
    pair("ui", "text", g_en, g_it)
    s_en, s_it = retail.read_pair(folder, "Spell", retail.read_spell_texts)
    for i, field in enumerate(("description", "aura")):
        pair("spell", field, {k: v[i] for k, v in s_en.items()}, {k: v[i] for k, v in s_it.items()})
    pair("ui", "text", *retail.read_pair(folder, "Spell", retail.read_subtexts))
    for prefix, table in FAMILY_TABLES.items():
        if retail.csv_path(folder, table, "enUS").is_file():
            reader: Callable[[Path], dict[str, str]] = lambda p, prefix=prefix: wago.read_family(p, prefix)  # noqa: E731
            pair("ui", "text", *retail.read_pair(folder, table, reader))
    pair("item", "description", *retail.read_pair(folder, "ItemSparse", retail.read_item_descriptions))
    return out


def merge_official(
    lines: list[dict[str, Any]],
    taken: dict[tuple[Any, str], str],
    prov: dict[str, Any],
    prov_of: dict[tuple[Any, str], dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """The import's `official` variants into a type's lines: per taken (id, field), the line's official
    variant is replaced (its ruling dropped when the text changed), else one is added (a new `pending` line
    when there is none); every other official variant is dropped, and a line left with no variant goes.
    Other variants are never edited. `prov_of`: a row's own provenance where it is not `prov` (a unit name
    from Wowhead). → (lines, official variants dropped)."""
    prov_of = prov_of or {}
    by = {(ln["id"], ln["field"]): ln for ln in lines}
    dropped = 0
    for k, line in list(by.items()):
        if k in taken:
            continue
        variants = decisions.variant_dicts(line)
        keep = [v for v in variants if not decisions.is_official(v["provenance"])]
        if len(keep) == len(variants):
            continue
        dropped += len(variants) - len(keep)
        if not keep:
            del by[k]
            continue
        if decisions.is_official(line["provenance"]):
            head, *rest = keep
            line["it"], line["provenance"] = head["it"], head["provenance"]
            for key in ("extra", "ruling"):
                line.pop(key, None)
                if head.get(key) is not None:
                    line[key] = head[key]
            line["conflicts"] = rest
            line["status"] = "pending"
        else:
            line["conflicts"] = keep[1:]
    for k, it in taken.items():
        p = prov_of.get(k, prov)
        if k not in by:
            by[k] = entry(k[0], k[1], it, prov=dict(p))
            continue
        line = by[k]
        official = [v for v in decisions.variant_dicts(line) if decisions.is_official(v["provenance"])]
        mine = official[0] if official else None
        if mine is None:
            line["conflicts"].append({"it": it, "provenance": dict(p)})
            continue
        if mine["it"] != it:
            mine["it"] = it
            mine.pop("ruling", None)
        mine["provenance"] = dict(p)
    return list(by.values()), dropped


def _creature_texts(
    path: Path, prov: dict[str, Any], date: str
) -> tuple[dict[tuple[Any, str], tuple[str, str]], dict[tuple[Any, str], dict[str, Any]]]:
    """pipeline/creature_official.tsv as (id, field) → (English, Italian), and the provenance of each row
    that is not `prov`'s (a Wowhead row: `wowhead@<date>`)."""
    texts: dict[tuple[Any, str], tuple[str, str]] = {}
    prov_of: dict[tuple[Any, str], dict[str, Any]] = {}
    wowhead = {**prov, "source": f"{WOWHEAD}@{date}"}
    for id_, field, en, it, fonte in creature_official.read_tsv(path):
        texts[(id_, field)] = (en, it)
        if fonte == WOWHEAD:
            prov_of[(id_, field)] = wowhead
    return texts, prov_of


def _verdict(type_: str, ln: dict[str, Any], r_en: str, r_it: str) -> tuple[str | None, str | None]:
    """The Italian a Forever English line `ln` takes from the official (English, Italian) pair → (it, None),
    or (None, the report counter)."""
    if not r_it.strip():
        return None, "no_italian"
    # a unit name is plain text, compared as it is (creature_official kept it the same way)
    same = r_en == ln["en"].strip() if type_ == "unit" else _hash(r_en) == ln["hash"]
    if not same:
        return None, "rejected_english_mismatch"
    if type_ == "ui":
        it, why = _ui_verdict(ln["en"], r_it)
    elif type_ == "unit":
        it, why = _name_verdict(ln["en"], r_it)
    else:
        it, why = convert_template(ln["en"], r_it)
    return (it, None) if it is not None else (None, _REASON[str(why)])


def run_official(
    retail_dir: Path,
    store: Path,
    build: str,
    date: str,
    *,
    placeholders_out: Path | None = None,
    addon_dir: Path | None = None,
    ambiguous_out: Path | None = None,
    creatures_file: Path | None = None,
) -> OfficialReport:
    """Import every type (read and judged before anything is written); the class / race words go to
    `placeholders_out` (default `placeholders.NAMES_FILE`), the UI groups left English for a ruling to
    `ambiguous_out` (default `AMBIGUOUS_FILE`, pipeline/ui_ambiguous.tsv). `addon_dir` (default: the
    repo's addon beside `store`) gives the UI keys' argument kinds and owned keys (`settle_ui`). The NPC
    names come from `creatures_file` (default pipeline/creature_official.tsv beside `store`); without it the
    unit lines are not touched."""
    if addon_dir is None:
        addon_dir = generate.default_addon_dir(Path(store))
    folder = Path(retail_dir)
    tables_stamp.check(retail.files(folder, TABLES), "wago", build)
    present = [t for t in FAMILY_TABLES.values() if retail.csv_path(folder, t, "enUS").is_file()]
    tables_stamp.check(retail.files(folder, present), "wago", build)
    prov = {"class": decisions.OFFICIAL, "source": f"{SOURCE}@{build}", "imported": date}
    texts = _retail_texts(folder)
    creatures = Path(creatures_file) if creatures_file else Path(store).parent / CREATURE_FILE
    types = list(TYPES)
    prov_of: dict[tuple[Any, str], dict[str, Any]] = {}
    if creatures.is_file():
        texts["unit"], prov_of = _creature_texts(creatures, prov, date)
    else:  # no creature file: the unit lines are left as they are, not emptied
        types.remove("unit")
    matcher = glossary_it.load_matcher(Path(store).parent)
    english, data = Store(store, english=True), Store(store)
    report = OfficialReport()
    review: list[tuple[str, str, str]] = []
    planned: dict[str, list[dict[str, Any]]] = {}
    for type_ in types:
        c = report.counts[type_]
        taken: dict[tuple[Any, str], str] = {}
        english_of: dict[Any, str] = {}
        for ln in english.load(type_):
            k = (ln["id"], ln["field"])
            if k not in texts[type_]:
                continue
            it, why = _verdict(type_, ln, *texts[type_][k])
            if it is None:
                c[str(why)] += 1
                continue
            # spec §8: the names the English holds, marked; interface text never is, and a unit line is the
            # name itself
            if type_ not in ("ui", "unit"):
                it = mark_from_english(it, ln["en"], matcher)
            new = entry(k[0], k[1], it, prov=dict(prov))
            problems = validate_line(type_, new)
            if problems:
                raise ValueError(f"official: {type_} {k[0]}/{k[1]}: {'; '.join(problems)}")
            taken[k] = it
            english_of[k[0]] = ln["en"]
            c["accepted"] += 1
        if type_ == "ui":
            review = settle_ui(taken, english_of, addon_dir, c)
        planned[type_], report.dropped[type_] = merge_official(data.load(type_), taken, prov, prov_of)
    names, report.absent_names = retail.read_placeholder_names(folder, placeholders.TOKENS)
    for type_ in types:
        data.save(type_, planned[type_], allow_empty=True)
    out = Path(placeholders_out) if placeholders_out else placeholders.NAMES_FILE
    out.write_text(placeholders.names_text(names, prov["source"]), encoding="utf-8")
    review_out = Path(ambiguous_out) if ambiguous_out else AMBIGUOUS_FILE
    review_out.write_text(ambiguous_text(review), encoding="utf-8")
    report.dropped = +report.dropped
    return report


def add_parser(sub: Any) -> None:
    of = sub.add_parser("official")
    of.add_argument("folder", help="the retail folder of `make wago-fetch-retail` (<table>.<locale>.csv)")
    of.add_argument("--build", required=True)
    of.add_argument("--date", required=True, help="YYYY-MM-DD, the provenance's `imported`")
    of.add_argument(
        "--names", type=Path, help="where the class / race words go (default: pipeline/placeholder_names.tsv)"
    )
    of.set_defaults(fn=run_cli)


def run_cli(a: argparse.Namespace) -> int:
    from wfj.paths import data_root

    date = dt.date.fromisoformat(a.date).isoformat()
    report = run_official(Path(a.folder), data_root(), a.build, date, placeholders_out=a.names)
    print(report.render())
    return 0
