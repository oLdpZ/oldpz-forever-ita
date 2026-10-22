"""Review focus 2: accented letters leave the writer as literal UTF-8 and read back equal."""

from wfj.core.model import entry, provenance
from wfj.emit import lua_writer
from wfj.io.lua_reader import parse_assignment

TEXT = "È perché la Città è lì"


def test_accents_roundtrip():
    ln = entry(1, "text", TEXT, prov=provenance("human", "t@1", "2026-10-21", translator="T"))
    ln["status"] = "trusted"
    ln["english"] = {"hash": "d311f9a5c36057a2", "src": "wdb@1"}
    rows = lua_writer.keyed_rows("book", [ln])
    shard = lua_writer.keyed_text("book", "d3", rows)
    raw = shard.encode("utf-8")
    assert TEXT.encode("utf-8") in raw  # literal bytes, no \ddd escapes
    assert b"\195" not in raw
    body = shard[shard.index("{", shard.index("WFJ.Data.add")) : shard.rindex(")")]
    _, table = parse_assignment("T = " + body)
    (row,) = [v for _, v in table.items]
    assert row.positional()[0] == TEXT
