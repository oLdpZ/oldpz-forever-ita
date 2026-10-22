"""Re-mark the stored Italian with the current glossary (spec §8, `core/names.mark_from_english`).

    python -m wfj.dev.remark_names

`import draft` / `import official` mark a line's names when it is imported; a term the glossary gains later
(`pipeline/glossario_curato.tsv`, a rebuilt official glossary) leaves the lines already stored unmarked. This
pass marks them: every variant (the line and its `conflicts`) of every type but `ui` (interface text, never
marked), for the terms the line's English holds. Idempotent: a marker already there is never searched, so a
second run changes nothing. Run `wfj check` and `wfj generate` after it.
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


def remark(data: Path) -> int:
    """Mark every stored variant again with the glossary beside `data` (in pipeline/); → markers added."""
    matcher = glossary_it.load_matcher(Path(data).parent)
    if matcher is None:
        return 0
    store, english = Store(data), Store(data, english=True)
    added = 0
    for type_ in TYPES:
        if type_ in UNMARKED_TYPES:
            continue
        lines = store.load(type_)
        if not lines:
            continue
        en = {(ln["id"], ln["field"]): ln["en"] for ln in english.load(type_)}
        changed = False
        for ln in lines:
            for v in decisions.variant_dicts(ln):
                it = v.get("it")
                if not isinstance(it, str):
                    continue
                marked = names.mark_from_english(it, en.get((ln["id"], ln["field"])), matcher)
                if marked != it:
                    added += marked.count(names.OPEN) - it.count(names.OPEN)
                    v["it"] = marked
                    changed = True
        if changed:
            store.save(type_, lines)
    return added


def main(argv: list[str]) -> int:
    if argv:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    n = remark(data_root())
    print(f"remark_names: {n} markers added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
