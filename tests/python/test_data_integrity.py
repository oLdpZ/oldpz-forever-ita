"""Invariants every committed `data/` must hold, whatever it ships, and the shapes the generator gives a shipped
line (on the small Italian fixture store, `tests/fixtures/it-store/`). The upstream Japanese corpus's counts and
floors went with that corpus; the store starts empty in Plan 1."""

import re

import pytest

from wfj.core import decisions
from wfj.core.report import SHIPPED
from wfj.io.jsonl_store import Store

TYPES = ("quest", "item", "spell", "gossip", "book", "ui", "objective", "area", "unit")
DRAFT = re.compile(r"^(?:draft|report)-[a-z0-9-]+@\d{4}-\d{2}-\d{2}$")


def test_every_variant_has_a_known_class_and_a_machine_one_names_its_draft(root):
    for type_ in TYPES:
        for ln in Store(root / "data").load(type_):
            for v in [ln, *ln["conflicts"]]:
                p = v["provenance"]
                assert p["class"] in ("human", "correction", "machine", "official"), (type_, ln["id"], p)
                if p["class"] == "machine":
                    assert DRAFT.match(p["source"]) and p.get("model"), (type_, ln["id"], p)


def test_every_rejected_hand_written_line_with_english_is_ruled(root):
    """A line with English and hand-written text that ships nothing carries a person's ruling on that text."""
    left = []
    for type_ in TYPES:
        english = {(e["id"], e["field"]) for e in Store(root / "data", english=True).load(type_)}
        for ln in Store(root / "data").load(type_):
            if ln["status"] == "rejected" and (ln["id"], ln["field"]) in english:
                left += [(type_, ln["id"], ln["field"]) for v in decisions.hand_written_variants(ln)
                         if not decisions.is_rejected(v)]
    assert left == []


@pytest.mark.parametrize("type_", ["item", "spell"])
def test_no_shipped_tooltip_asks_for_more_slots_than_its_english_prints(root, type_):
    """A `$N<k>` or `$D<k>` past what the template prints can never be filled, so the line falls back to English
    for every player. Shipped tooltip rows stay within `align.value_slots` / `align.duration_slots`."""
    from wfj.core import align

    english = {(ln["id"], ln["field"]): ln["en"] for ln in Store(root / "data", english=True).load(type_)}
    over = []
    for ln in Store(root / "data").load(type_):
        en = english.get((ln["id"], ln["field"]))
        if ln["status"] not in SHIPPED or en is None:
            continue
        slots, durations = align.value_slots(en), align.duration_slots(en)
        if slots is None:
            continue
        n = max((int(m) for m in re.findall(r"\$N(\d+)", ln["it"])), default=0)
        d = max((int(m) for m in re.findall(r"\$D(\d+)", ln["it"])), default=0)
        if n > slots or (durations is not None and d > durations):
            over.append((ln["id"], ln["field"], n, slots, d, durations))
    assert not over, f"{len(over)} shipped {type_} line(s) ask for a slot the English never prints: {over[:10]}"


# ---- the generated shape, on the Italian fixture store ---------------------------------------------------------


def test_generated_shard_carries_paragraph_breaks_and_literal_accents(it_planned):
    shard = it_planned["Data/Quest/Quest_0000.lua"]
    row = next(line for line in shard.splitlines() if line.strip().startswith("[7] ="))
    assert "\\n\\n" in row  # Lua-escaped newlines inside the completion slot
    assert "Il tuo primo compito è fare pulizia, {name}." in row  # UTF-8 as written, tokens kept literal


def test_shipped_progress_and_completion_record_their_own_english(it_store, it_planned):
    """ADR-019: a shipped progress / completion line records its own English hash, and the generated row's
    completion h1 slot carries its first 32 bits."""
    english = {(ln["id"], ln["field"]): ln for ln in Store(it_store, english=True).load("quest")}
    by = {(ln["id"], ln["field"]): ln for ln in Store(it_store).load("quest")}
    for field in ("progress", "completion"):
        en = english[(7, field)]
        assert by[(7, field)]["english"] == {"hash": en["hash"], "src": en["src"]}
    h = by[(7, "completion")]["english"]["hash"]
    row = next(line for line in it_planned["Data/Quest/Quest_0000.lua"].splitlines() if line.startswith("  [7] = {"))
    assert row.rstrip(",").rsplit(", ", 2)[-2] == f"0x{h[:8]}"  # slot 10: completion h1
