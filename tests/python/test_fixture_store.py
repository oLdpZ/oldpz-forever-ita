"""The committed Italian fixture store and its generated shards are what `python -m wfj.dev.fixture_store` writes."""

from pathlib import Path

from wfj.dev import fixture_store


def _tree(base: Path) -> dict[str, bytes]:
    return {p.relative_to(base).as_posix(): p.read_bytes() for p in sorted(base.rglob("*")) if p.is_file()}


def test_the_committed_fixture_is_a_regeneration(root: Path, tmp_path: Path):
    fixture_store.write(root, tmp_path)
    committed = _tree(root / "tests" / "fixtures" / "it-store")
    fresh = _tree(tmp_path)
    assert sorted(committed) == sorted(fresh), "run `python -m wfj.dev.fixture_store` (from pipeline/)"
    assert committed == fresh, "run `python -m wfj.dev.fixture_store` (from pipeline/)"


def test_the_fixture_shards_follow_the_toc_order(root: Path):
    addon = root / "tests" / "fixtures" / "it-store" / "addon"
    files = (addon / "files.txt").read_text(encoding="utf-8").split()
    assert files[:2] == ["Data/Meta.lua", "Data/Vectors.lua"] and len(files) > 2
    assert all((addon / f).is_file() for f in files)
