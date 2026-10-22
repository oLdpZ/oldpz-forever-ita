"""`wfj check` over gossip: the key is the English hash (ADR-005 / ADR-017): Italian required, hand-written
before machine, trusted with english {hash: key}, never stale; `validate` agrees; the draft importer writes gossip."""

from pathlib import Path

from wfj.cmd import validate
from wfj.cmd.check import GOSSIP_SRC, gossip_scopes
from wfj.cmd.import_ import run as import_run
from wfj.core.align import load_allowlist
from wfj.core.hashing import key
from wfj.core.model import entry, provenance
from wfj.core.normalize import normalize_v1
from wfj.core.status import decide
from wfj.io.jsonl_store import Store

EN = "Ah, the beauty of Shadowglen never ceases to delight my senses!"
K = key(normalize_v1(EN))
MACHINE = {"class": "machine", "model": "model-x", "source": "draft-t@2026-09-14", "imported": "2026-09-14"}


def _decide(line, english=None):
    scope = gossip_scopes([line], english=english)[line["id"]]
    return decide(line, scope, load_allowlist(""), scope.hashes["text"])


def test_italian_gossip_is_trusted_and_its_english_unchanged_is_rejected():
    it = "Ah, la bellezza di Shadowglen non smette mai di deliziare i miei sensi!"
    d = _decide(entry(K, "text", it, prov=MACHINE), {K: EN})
    assert (d.status, d.reasons, d.checks) == ("trusted", [], [])
    d = _decide(entry(K, "text", EN, prov=MACHINE), {K: EN})
    assert (d.status, d.reasons) == ("rejected", ["not_italian"])
    d = _decide(entry(K, "text", "シャドウグレン", prov=MACHINE))  # no Latin letter, with or without the English
    assert (d.status, d.reasons) == ("rejected", ["not_italian"])


def test_hand_written_gossip_beats_a_machine_draft():
    human = provenance("human", "community@2026-09-14", "2026-09-14", translator="someone")
    line = entry(K, "text", "Traduzione della macchina", prov=MACHINE,
                 conflicts=[{"it": "Traduzione di una persona", "provenance": human}])
    d = _decide(line)
    assert d.status == "trusted" and d.winner == 1  # the human variant is promoted


def test_a_gossip_line_is_never_stale():
    line = entry(K, "text", "Traduzione", prov=MACHINE)
    line["english"] = {"hash": K, "src": GOSSIP_SRC}
    assert _decide(line).status == "trusted"


def test_draft_check_validate_round_trip(tmp_path: Path, monkeypatch):
    from wfj.cmd import check

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "SCHEMA").write_text("1\n")
    (tmp_path / "pipeline").mkdir()
    (tmp_path / "pipeline" / "allowlist.txt").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "content").mkdir(parents=True)
    (tmp_path / "docs" / "content" / "translation-style-guide.md").write_text("version: sg1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    draft = tmp_path / "draft.jsonl"
    draft.write_text(f'{{"id": "{K}", "field": "text", "it": "Ah, la bellezza di Shadowglen!"}}\n', encoding="utf-8")
    assert import_run(["draft", "gossip", str(draft), "--model", "model-x", "--date", "2026-09-14",
                       "--name", "gossip-sg1"]) == 0
    assert check.run([]) == 0
    (line,) = Store(tmp_path / "data").load("gossip")
    assert line["status"] == "trusted"
    assert line["english"] == {"hash": K, "src": GOSSIP_SRC}
    assert line["provenance"]["class"] == "machine"
    assert validate.rule_referential(Store(tmp_path / "data"), Store(tmp_path / "data", english=True)) == []
    assert check.run([]) == 0  # idempotent
    assert Store(tmp_path / "data").load("gossip") == [line]


def test_dots_only_italian_for_dots_only_english_is_trusted():
    # the draft lint's rule ("..." may be translated as "…") holds in check too
    dots = key(normalize_v1("..."))
    line = entry(dots, "text", "…", prov=MACHINE)
    scope = gossip_scopes([line], {dots})[dots]
    d = decide(line, scope, load_allowlist(""), scope.hashes["text"])
    assert (d.status, d.reasons) == ("trusted", [])
    # without the dots-only English it is not Italian; and the English unchanged stays rejected under dots English
    assert _decide(line).reasons == ["not_italian"]
    kept = entry(dots, "text", "...", prov=MACHINE)
    scope = gossip_scopes([kept], set(), {dots: "..."})[dots]
    assert decide(kept, scope, load_allowlist(""), scope.hashes["text"]).reasons == ["not_italian"]


def test_a_gossip_line_ruled_kept_english_is_trusted():
    # a name-only label ("Zul'Farrak") carries `ruling: accept` and ships as its English, no marker
    k = key(normalize_v1("Zul'Farrak"))
    ruling = {"ruling": "accept", "by": "maintainer", "date": "2026-09-27", "note": "a name"}
    d = _decide(entry(k, "text", "Zul'Farrak", prov=MACHINE) | {"ruling": ruling}, {k: "Zul'Farrak"})
    assert (d.status, d.reasons) == ("trusted", [])
    assert _decide(entry(k, "text", "Zul'Farrak", prov=MACHINE), {k: "Zul'Farrak"}).reasons == ["not_italian"]
