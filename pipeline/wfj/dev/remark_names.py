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
"""

from __future__ import annotations

import sys
from pathlib import Path

from wfj.cmd.check import TYPES
from wfj.cmd.import_draft import UNMARKED_TYPES
from wfj.core import decisions, names
from wfj.dev import glossary_it
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

# the kinds also found by their English form in the Italian (an NPC name a text left in English)
ENGLISH_KINDS = frozenset({glossary_it.CREATURE_KIND})
UNIT_TYPE = glossary_it.STORE_TYPES[glossary_it.CREATURE_KIND]


def remark(data: Path, conflicts: list[str] | None = None, counts: dict[str, int] | None = None) -> int:
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
    n = remark(data_root(), conflicts, counts)
    for line in conflicts:
        print(f"remark_names: NPC name with two Italian forms: {line}")
    shown = ", ".join(f"{t} {k}" for t, k in sorted(counts.items())) or "none"
    print(f"remark_names: {n} markers added ({shown})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
