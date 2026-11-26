"""`wfj import english upstream`: the English the Japanese project ships that we lack, additive only."""

import json
import subprocess
from pathlib import Path

from wfj.cmd.import_ import run
from wfj.core.hashing import key
from wfj.core.model import english_line
from wfj.core.normalize import normalize_for
from wfj.io import upstream
from wfj.io.jsonl_store import Store

UP_SRC = "wdb@1.60.1.71037"


def _data_dir(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "SCHEMA").write_text("1\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path / "data"


def _up(type_: str, id_, field: str, en: str, src: str = UP_SRC, **extra) -> dict:
    h = key(normalize_for(type_, en))
    return {"id": id_, "field": field, "en": en, "hash": h, "src": src, **extra}


def _clone(tmp_path: Path, rows: dict[str, list[dict]]) -> tuple[Path, str]:
    clone = tmp_path / "clone"
    for type_, lines in rows.items():
        d = clone / "data" / "english" / type_
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{type_}-0000.jsonl").write_text(
            "".join(json.dumps(ln) + "\n" for ln in lines), encoding="utf-8"
        )
    git = ["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "x"], check=True)
    sha = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    return clone, sha


def _ours(type_: str, id_, field: str, en: str, src: str = "wdb@1.15.9.69722") -> dict:
    return english_line(id_, field, en, key(normalize_for(type_, en)), src)


def _store(data: Path) -> Store:
    return Store(data, english=True)


def _snapshot(data: Path) -> dict[str, bytes]:
    return {str(p.relative_to(data)): p.read_bytes() for p in sorted((data / "english").rglob("*.jsonl"))}


def _go(clone: Path, sha: str, *extra: str) -> int:
    return run(["english", "upstream", str(clone), "--commit", sha[:8], *extra])


def test_upstream_adds_missing_quest(tmp_path: Path, monkeypatch):
    data = _data_dir(tmp_path, monkeypatch)
    clone, sha = _clone(
        tmp_path,
        {"quest": [_up("quest", 90001, "title", "New one"), _up("quest", 90001, "description", "Go. Now.")]},
    )
    assert _go(clone, sha) == 0
    by = {(ln["id"], ln["field"]): ln for ln in _store(data).load("quest")}
    assert set(by) == {(90001, "title"), (90001, "description")}
    for ln in by.values():
        assert ln["src"] == UP_SRC
        assert ln["hash"] == key(normalize_for("quest", ln["en"]))


def test_upstream_keeps_ours_and_reports_conflict(tmp_path: Path, monkeypatch):
    data = _data_dir(tmp_path, monkeypatch)
    _store(data).save("quest", [_ours("quest", 5, "title", "A")])
    clone, sha = _clone(tmp_path, {"quest": [_up("quest", 5, "title", "B")]})
    report = tmp_path / "rep.tsv"
    assert _go(clone, sha, "--report", str(report)) == 0
    assert [ln["en"] for ln in _store(data).load("quest")] == ["A"]
    assert "quest\t5\ttitle\tA\tB" in report.read_text(encoding="utf-8").splitlines()


def test_upstream_fills_missing_field_of_known_quest(tmp_path: Path, monkeypatch):
    data = _data_dir(tmp_path, monkeypatch)
    _store(data).save("quest", [_ours("quest", 7, "title", "Seven")])
    clone, sha = _clone(
        tmp_path,
        {"quest": [_up("quest", 7, "title", "Seven"), _up("quest", 7, "completion", "Well done.")]},
    )
    assert _go(clone, sha) == 0
    by = {(ln["id"], ln["field"]): ln for ln in _store(data).load("quest")}
    assert set(by) == {(7, "title"), (7, "completion")}
    assert by[(7, "title")]["src"] == "wdb@1.15.9.69722"
    assert by[(7, "completion")]["src"] == UP_SRC


def test_upstream_drops_placeholder_quest_whole(tmp_path: Path, monkeypatch):
    data = _data_dir(tmp_path, monkeypatch)
    clone, sha = _clone(
        tmp_path,
        {
            "quest": [
                _up("quest", 90002, "title", "Real"),
                _up("quest", 90002, "description", "temp text 02"),
                _up("quest", 90003, "title", "<unused>"),
                _up("quest", 90003, "description", "Fine."),
                _up("quest", 90004, "title", "Keep"),
            ]
        },
    )
    assert _go(clone, sha) == 0
    assert {ln["id"] for ln in _store(data).load("quest")} == {90004}


def test_upstream_gossip_bad_hash_skipped(tmp_path: Path, monkeypatch, capsys):
    data = _data_dir(tmp_path, monkeypatch)
    good = _up("gossip", key(normalize_for("gossip", "Hello.")), "text", "Hello.", npcs=[3, 9])
    bad = _up("gossip", "0123456789abcdef", "text", "Bye.")
    clone, sha = _clone(tmp_path, {"gossip": [good, bad]})
    assert _go(clone, sha) == 0
    got = _store(data).load("gossip")
    assert [ln["id"] for ln in got] == [good["id"]] and got[0]["npcs"] == [3, 9]
    assert "1 hash diversi" in capsys.readouterr().out


def test_upstream_idempotent(tmp_path: Path, monkeypatch):
    data = _data_dir(tmp_path, monkeypatch)
    _store(data).save("quest", [_ours("quest", 5, "title", "A")])
    clone, sha = _clone(
        tmp_path,
        {
            "quest": [_up("quest", 5, "title", "B"), _up("quest", 90001, "title", "New")],
            "objective": [_up("objective", 11, "text", "Kill 5 rats")],
            "book": [_up("book", 12, "text", "Dear diary")],
        },
    )
    assert _go(clone, sha) == 0
    first = _snapshot(data)
    assert _go(clone, sha) == 0
    assert _snapshot(data) == first
    assert len(first) == 4  # quest shards by id range: two quest shards, one objective, one book


def test_upstream_rejects_wrong_commit(tmp_path: Path, monkeypatch, capsys):
    data = _data_dir(tmp_path, monkeypatch)
    clone, _ = _clone(tmp_path, {"quest": [_up("quest", 90001, "title", "New")]})
    assert run(["english", "upstream", str(clone), "--commit", "deadbeef"]) != 0
    assert "deadbeef" in capsys.readouterr().err
    assert _snapshot(data) == {}
    assert not (tmp_path / "pipeline" / "upstream-source.txt").exists()


def test_upstream_dry_run_writes_nothing(tmp_path: Path, monkeypatch, capsys):
    data = _data_dir(tmp_path, monkeypatch)
    clone, sha = _clone(tmp_path, {"quest": [_up("quest", 90001, "title", "New")]})
    assert _go(clone, sha, "--dry-run") == 0
    assert _snapshot(data) == {}
    assert not (tmp_path / "pipeline" / "upstream-source.txt").exists()
    assert "english quest: +1 righe (1 missioni nuove)" in capsys.readouterr().out


def test_upstream_writes_stamp(tmp_path: Path, monkeypatch):
    _data_dir(tmp_path, monkeypatch)
    clone, sha = _clone(tmp_path, {"quest": [_up("quest", 90001, "title", "New")]})
    assert _go(clone, sha) == 0
    assert (tmp_path / "pipeline" / "upstream-source.txt").read_text() == f"wfj-upstream {sha}\n"


def test_add_missing_and_placeholders():
    from wfj.cmd.import_english import add_missing

    ours = [_ours("quest", 1, "title", "A")]
    merged, added, conflicts = add_missing(ours, [_up("quest", 1, "title", "A"), _up("quest", 1, "description", "D"), _up("quest", 1, "completion", "Z")])
    assert added == 2 and not conflicts and len(merged) == 3
    _, _, conflicts = add_missing(ours, [_up("quest", 1, "title", "B")])
    assert conflicts == [(1, "title", "A", "B")]
    assert upstream.placeholder_quest_ids([_up("quest", 3, "title", "TEST quest"), _up("quest", 4, "title", "OK")]) == {3}
