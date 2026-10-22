"""The emit layout follows model.FIELDS and its status codes are the checked ones."""

from wfj.core import model
from wfj.emit import schema


def test_slots_follow_model_fields():
    for type_ in schema.TYPES:
        fields = model.FIELDS[type_]
        s = schema.SLOTS[type_]
        assert s["fields"] == fields
        assert s["hash"] == len(fields)
        assert s["status"] == 2 * len(fields) + 1
    # the female-variant h1 slots follow the status string, quest only
    assert schema.SLOTS["quest"]["female"] == 2 * len(model.FIELDS["quest"]) + 1 == 11
    assert all("female" not in schema.SLOTS[t] for t in ("item", "spell", "ui"))


def test_status_chars_are_the_shipped_statuses():
    assert set(schema.STATUS_CHAR) == {"trusted", "stale", "unaligned"}
    assert set(schema.STATUS_CHAR) <= set(model.STATUSES)
    assert schema.MISSING not in schema.STATUS_CHAR.values()
    # `e`: a keep-English decision (pipeline/keep_english.tsv), shown as the client's English, no marker
    assert len({*schema.STATUS_CHAR.values(), schema.MISSING, schema.KEPT}) == 5


def test_the_addon_status_table_is_the_twin_of_the_schema_codes():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    const = (root / "addon/OldpZ_ForeverITA/Core/Const.lua").read_text(encoding="utf-8")
    line = re.search(r"^WFJ\.STATUS = \{(.*)\}$", const, re.M).group(1)
    codes = {a or b: n for a, b, n in re.findall(r'(?:\["(.)"\]|(\w)) = "(\w+)"', line)}
    assert codes == {
        **{c: s for s, c in schema.STATUS_CHAR.items()}, schema.MISSING: "missing", schema.KEPT: "english"
    }


def test_shard_relpaths():
    assert schema.shard_relpath("quest", 7) == "Data/Quest/Quest_0007.lua"
    assert schema.shard_relpath("gossip", "ab") == "Data/Gossip/Gossip_ab.lua"
    assert schema.shard_of(999) == 0 and schema.shard_of(1000) == 1 and schema.shard_of(2468) == 2
