"""Keep-English draft rows (`{"ref": …, "it": null}`): a line that correctly stays English, such as a quest
title that is only a proper name. The lint accepts it as `kept_english` (neither translated nor failed), it is
never expanded into an import file, and `translate_batch keep` records it in `pipeline/keep_english.tsv`
keyed by type, id, field and the English hash, so `cut` skips it until the English changes."""

import json

from wfj.dev import translate_batch as tb
from wfj.dev import translate_lint as tl
from wfj.io.jsonl_store import Store


def _batch(tmp_path):
    rows = [
        {"ref": "r1", "kind": "quest_title", "en": "Milly Osworth", "targets": [[1, "title"]]},
        {"ref": "r2", "kind": "quest_title", "en": "The Fargodeep Mine", "targets": [[2, "title"]]},
    ]
    batch, draft = tmp_path / "b.jsonl", tmp_path / "b.draft.jsonl"
    tb.write_jsonl(batch, rows)
    tb.write_jsonl(draft, [{"ref": "r1", "it": None}, {"ref": "r2", "it": "La miniera di Fargodeep"}])
    return batch, draft


def test_lint_accepts_a_null_row_as_kept_english(tmp_path, capsys):
    batch, draft = _batch(tmp_path)
    (tmp_path / "none.txt").write_text("", encoding="utf-8")
    assert tl.main([str(batch), str(draft), "--allowlist", str(tmp_path / "none.txt")]) == 0
    out = capsys.readouterr().out
    assert "1 ok" in out and "1 kept_english" in out and "0 failed" in out
    ok = [json.loads(x) for x in (tmp_path / "b.draft.ok.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["ref"] for r in ok] == ["r2"]  # the kept row is not a translation
    kept = [json.loads(x) for x in (tmp_path / "b.draft.keep.jsonl").read_text(encoding="utf-8").splitlines()]
    assert kept == [{"ref": "r1", "kind": "quest_title", "en": "Milly Osworth", "targets": [[1, "title"]]}]


def test_a_null_row_still_counts_for_missing_and_duplicate(tmp_path):
    batch, draft = _batch(tmp_path)
    tb.write_jsonl(draft, [{"ref": "r1", "it": None}, {"ref": "r1", "it": None}])
    ok, kept, failures = tl.lint_rows(batch, draft, set())
    assert failures["r1"] == ["duplicate"] and failures["r2"] == ["missing"]
    assert ok == [] and kept == []


def test_a_row_without_it_is_not_kept(tmp_path):
    batch, draft = _batch(tmp_path)
    tb.write_jsonl(draft, [{"ref": "r1"}, {"ref": "r2", "it": "La miniera di Fargodeep"}])
    _, kept, failures = tl.lint_rows(batch, draft, set())
    assert kept == [] and failures == {"r1": ["not_italian"]}


def _repo(tmp_path, title="Milly Osworth", hash_="a" * 16):
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "SCHEMA").write_text("1\n")
    (tmp_path / "docs" / "content").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "content" / "translation-style-guide.md").write_text("# guide\n\nversion: sg1\n")
    (tmp_path / "pipeline").mkdir(exist_ok=True)
    Store(data, english=True).save("quest", [
        {"id": 1, "field": "title", "en": title, "hash": hash_, "src": "wdb@1.60.1.70450"},
        {"id": 2, "field": "title", "en": "The Fargodeep Mine", "hash": "b" * 16, "src": "wdb@1.60.1.70450"},
    ])
    return data


def test_cut_skips_a_kept_line_until_its_english_changes(tmp_path):
    data = _repo(tmp_path)
    keep = tmp_path / "keep.jsonl"
    tb.write_jsonl(keep, [{"ref": "r1", "kind": "quest_title", "en": "Milly Osworth", "targets": [[1, "title"]]}])
    assert tb.record_kept(data, [keep]) == 1
    table = (tmp_path / "pipeline" / "keep_english.tsv").read_text(encoding="utf-8").splitlines()
    assert table == ["tipo\tid\tcampo\thash\ten", f"quest\t1\ttitle\t{'a' * 16}\tMilly Osworth"]
    assert tb.record_kept(data, [keep]) == 1  # recording again changes nothing
    assert (tmp_path / "pipeline" / "keep_english.tsv").read_text(encoding="utf-8").splitlines() == table
    rows = tb.cut(data, "quest_title", 10, tmp_path / "c1.jsonl")
    assert [t for r in rows for t in r["targets"]] == [[2, "title"]]
    # a patch rewords the English: the decision no longer holds and the line is cut again
    _repo(tmp_path, title="Milly Osworth's Farm", hash_="c" * 16)
    rows = tb.cut(data, "quest_title", 10, tmp_path / "c2.jsonl")
    assert sorted(t[0] for r in rows for t in r["targets"]) == [1, 2]


def _kept_and_translated(tmp_path, kept_hash="a" * 16):
    """Quest 1's title kept English (decision on `kept_hash`), quest 2's title translated."""
    data = _repo(tmp_path)
    (tmp_path / "pipeline" / "keep_english.tsv").write_text(
        f"{tb.KEEP_HEADER}\nquest\t1\ttitle\t{kept_hash}\tMilly Osworth\n", encoding="utf-8"
    )
    Store(data).save("quest", [{
        "id": 2, "field": "title", "it": "La miniera di Fargodeep", "status": "trusted", "checks": [],
        "reasons": [], "conflicts": [], "english": {"hash": "b" * 16, "src": "wdb@1.60.1.70450"},
        "provenance": {"class": "machine", "model": "m", "source": "draft-x-sg1@2026-10-21",
                       "imported": "2026-10-21"},
    }])
    return data


def _quest_rows(data):
    from wfj.cmd import generate

    planned = generate.plan(Store(data), [])
    return "".join(t for p, t in planned.items() if p.startswith("Data/Quest/"))


def test_a_kept_line_ships_as_intentionally_english(tmp_path):
    """A keep-list line whose English is still the decided one ships status `e` (no text, its h1), so the
    addon shows the client's English with no missing marker; quest 1 gets a row for it alone."""
    from wfj.emit import lua_writer, schema

    shard = _quest_rows(_kept_and_translated(tmp_path))
    status = schema.KEPT + schema.MISSING * 4
    assert f'[1] = {{ nil, nil, nil, nil, nil, {lua_writer.h1_literal("a" * 16)}, nil, nil, nil, nil, "{status}" }},' in shard


def test_a_kept_line_whose_english_changed_ships_missing(tmp_path):
    shard = _quest_rows(_kept_and_translated(tmp_path, kept_hash="f" * 16))
    assert "[1] =" not in shard


def test_keep_drops_a_kept_line_that_now_has_a_translation(tmp_path):
    """`translate_batch keep` (every import runs it) drops a keep-list row once an Italian line exists."""
    data = _kept_and_translated(tmp_path)
    (tmp_path / "pipeline" / "keep_english.tsv").write_text(
        f"{tb.KEEP_HEADER}\nquest\t1\ttitle\t{'a' * 16}\tMilly Osworth\n"
        f"quest\t2\ttitle\t{'b' * 16}\tThe Fargodeep Mine\n", encoding="utf-8"
    )
    tb.record_kept(data, [])
    table = (tmp_path / "pipeline" / "keep_english.tsv").read_text(encoding="utf-8").splitlines()
    assert table == [tb.KEEP_HEADER, f"quest\t1\ttitle\t{'a' * 16}\tMilly Osworth"]
