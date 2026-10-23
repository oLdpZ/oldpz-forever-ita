"""Re-mark the stored Italian with the current glossary (spec §8, `core/names.mark_from_english`).

    python -m wfj.dev.remark_names

`import draft` / `import official` mark a line's names when it is imported; a term the glossary gains later
(`pipeline/glossario_curato.tsv`, a rebuilt official glossary) leaves the lines already stored unmarked. This
pass marks them: every variant (the line and its `conflicts`) of every type but `ui` (interface text, never
marked), for the terms the line's English holds. Idempotent: a marker already there is never searched, so a
second run changes nothing. Run `wfj check` and `wfj generate` after it.

NPC names come from the `unit` table too (`glossary_it.load_marker_matcher`: official and machine names), so
the name the world shows is the one the text shows. An NPC name is marked where the Italian holds its Italian
form, or where the Italian left it in English (`Senani Thunderheart` → `⟦Senani Thunderheart=Senani Cuore
Tonante⟧`): no other word of the Italian changes. Two Italian names for one English are reported.

Spec §5b (the official form wins and rewrites the texts; one NPC, one Italian name): before marking, every
creature id sharing an English name takes that name's one form where its Italian is a machine draft
(`harmonise`); after marking, an NPC-name marker whose Italian is no longer the form is rewritten
(`rewrite_markers`: a marker is never searched, so marking alone would keep an old draft's name).
`wfj validate` refuses data where either does not hold (`rule_unit_names`).
"""

from __future__ import annotations

import sys
from pathlib import Path

from wfj.cmd.check import TYPES
from wfj.cmd.import_draft import UNMARKED_TYPES
from wfj.core import decisions, names
from wfj.core.report import SHIPPED
from wfj.dev import glossary_it
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

# the kinds also found by their English form in the Italian (an NPC name a text left in English)
ENGLISH_KINDS = frozenset({glossary_it.CREATURE_KIND})
UNIT_TYPE = glossary_it.STORE_TYPES[glossary_it.CREATURE_KIND]


def remark(
    data: Path,
    conflicts: list[str] | None = None,
    counts: dict[str, int] | None = None,
    stats: dict[str, int] | None = None,
) -> int:
    """The whole pass, in order: `harmonise` (every creature id sharing an English name ships its one
    Italian), `mark` (the new markers), `rewrite_markers` (an NPC-name marker whose Italian is no longer the
    unit form).
    → changes made (names harmonised + markers added + markers rewritten); `stats` gets each of the three
    (`harmonised`, `added`, `rewritten`), `conflicts` and `counts` as `mark`."""
    harmonised = harmonise(data)
    added = mark(data, conflicts, counts)
    rewritten = rewrite_markers(data)
    if stats is not None:
        stats.update(harmonised=harmonised, added=added, rewritten=rewritten)
    return harmonised + added + rewritten


def harmonise(data: Path) -> int:
    """Spec §5b, one NPC one name: a shipped `unit` `name` line (`SHIPPED`, the lines `wfj validate` counts)
    whose Italian is not its English's one form (`glossary_it.unit_forms`: the official one, else the most
    common) takes that form when its Italian is a MACHINE draft (a ruling on the old text is dropped). A line
    whose winning Italian is official or a person's is left as it is: two such forms for one English need a
    person (`wfj validate` refuses them, `rule_unit_names`). → lines changed"""
    store, english = Store(data), Store(data, english=True)
    forms = glossary_it.unit_forms(store, english)
    en_of = {ln["id"]: ln["en"].strip() for ln in english.load(UNIT_TYPE) if ln["field"] == "name"}
    lines = store.load(UNIT_TYPE)
    n = 0
    for ln in lines:
        if ln["field"] != "name" or ln.get("status") not in SHIPPED or not isinstance(ln.get("it"), str):
            continue
        form = forms.get(en_of.get(ln["id"], ""))
        if form is None or ln["it"].strip() == form or not decisions.is_machine(ln["provenance"]):
            continue
        ln["it"] = form
        ln.pop("ruling", None)
        n += 1
    if n:
        store.save(UNIT_TYPE, lines)
    return n


def stale_marker(forms: dict[str, str], en: str, it: str) -> str | None:
    """The text an NPC-name marker `⟦en=it⟧` must become, or None when it is right (or no NPC name's): the
    marker of the current form (`glossary_it.npc_marker_forms`), or the bare English when the name stays
    English. The rule `wfj validate` checks (`rule_unit_names`)."""
    form = forms.get(en)
    if form is None or form == it or any(c in form for c in (names.OPEN, names.CLOSE, names.SEP)):
        return None
    return en if form == en else f"{names.OPEN}{en}{names.SEP}{form}{names.CLOSE}"


def rewrite_markers(data: Path) -> int:
    """`mark_names` never searches inside a marker, so a marker keeps the Italian it was written with. Every
    NPC-name marker (its English one of the unit table's names, not another kind's glossary term) whose
    Italian differs from the current form is rewritten to it, in every variant of every type but `ui`: the
    `unit` lines first (a name inside a longer name), then the others against the forms they now give. A
    glossary term's marker is left as it is: such a term may have several right forms (male / female, a
    derived short form).
    Idempotent. → markers rewritten"""
    repo = Path(data).parent
    store = Store(data)
    n = 0
    for group in ((UNIT_TYPE,), tuple(t for t in TYPES if t != UNIT_TYPE and t not in UNMARKED_TYPES)):
        forms = glossary_it.npc_marker_forms(repo)
        for type_ in group:
            lines = store.load(type_)
            changed = 0
            for ln in lines:
                for v in decisions.variant_dicts(ln):
                    it = v.get("it")
                    if not isinstance(it, str) or names.OPEN not in it:
                        continue
                    hits = 0

                    def sub(m, forms=forms):
                        nonlocal hits
                        new = stale_marker(forms, m.group(1), m.group(2))
                        hits += new is not None
                        return m.group(0) if new is None else new

                    out = names.MARK.sub(sub, it)
                    if hits:
                        v["it"] = out
                        changed += hits
            if changed:
                store.save(type_, lines)
                n += changed
    return n


def mark(data: Path, conflicts: list[str] | None = None, counts: dict[str, int] | None = None) -> int:
    """Mark every stored variant again with the glossary beside `data` (in pipeline/) and the unit table's NPC
    names; → markers added. `conflicts` gets the NPC names with two Italian forms, `counts` the markers added
    per type."""
    names_matcher = glossary_it.load_marker_matcher(Path(data).parent, conflicts)
    if names_matcher is None:
        return 0
    glossary_matcher = glossary_it.load_matcher(Path(data).parent)
    store, english = Store(data), Store(data, english=True)
    added = 0
    for type_ in TYPES:
        if type_ in UNMARKED_TYPES:
            continue
        lines = store.load(type_)
        if not lines:
            continue
        # an NPC name (the unit table's own line): only the glossary's names inside it are marked, never the
        # whole name as itself (`Flesh Eater` stays as it is; `Hungry Dire Wolf` marks `Dire Wolf`)
        unit = type_ == UNIT_TYPE
        matcher, kinds = (glossary_matcher, ()) if unit else (names_matcher, ENGLISH_KINDS)
        en = {(ln["id"], ln["field"]): ln["en"] for ln in english.load(type_)}
        changed = False
        for ln in lines:
            line_en = en.get((ln["id"], ln["field"]))
            for v in decisions.variant_dicts(ln):
                it = v.get("it")
                if not isinstance(it, str):
                    continue
                if unit:
                    found = matcher.find(line_en) if matcher is not None and line_en else []
                    marked = names.mark_names(it, [t for t in found if t[0] != line_en.strip()])
                else:
                    marked = names.mark_from_english(it, line_en, matcher, kinds)
                if marked != it:
                    n = marked.count(names.OPEN) - it.count(names.OPEN)
                    added += n
                    if counts is not None:
                        counts[type_] = counts.get(type_, 0) + n
                    v["it"] = marked
                    changed = True
        if changed:
            store.save(type_, lines)
    return added


def main(argv: list[str]) -> int:
    if argv:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    conflicts: list[str] = []
    counts: dict[str, int] = {}
    stats: dict[str, int] = {}
    remark(data_root(), conflicts, counts, stats)
    for line in conflicts:
        print(f"remark_names: NPC name with two Italian forms: {line}")
    shown = ", ".join(f"{t} {k}" for t, k in sorted(counts.items())) or "none"
    print(f"remark_names: {stats['harmonised']} NPC names harmonised to their one form")
    print(f"remark_names: {stats['added']} markers added ({shown})")
    print(f"remark_names: {stats['rewritten']} NPC-name markers rewritten to the current form")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
