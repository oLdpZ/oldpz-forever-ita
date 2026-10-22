"""`wfj import official`: the retail itIT texts (wago.tools) land in data/ as `official` variants, only where
the retail English for the same id is the English Forever shows, with the same format specifiers (UI) and the
same value slots (item / spell templates, converted to the addon's `$N<k>` / `$D<k>` placeholders as a draft
writes them). Review Focus 1 and 3 of the plan."""

import shutil
from pathlib import Path

import pytest

from wfj.cmd import check
from wfj.cmd.import_ import run as import_run
from wfj.cmd.import_official import convert_template, run_official
from wfj.core import placeholders
from wfj.core.hashing import key as hash_key
from wfj.core.model import english_line, entry, validate_line
from wfj.core.normalize import normalize_for
from wfj.emit import lua_writer
from wfj.io import retail
from wfj.io.jsonl_store import Store

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "retail"
BUILD = "12.1.5.70448"
DATE = "2026-10-21"
FOREVER = "db2@1.60.1.70450"


def _en(id_, field, en):
    return english_line(id_, field, en, hash_key(normalize_for("item", en)), FOREVER)


def _setup(tmp_path: Path, monkeypatch) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "SCHEMA").write_text("1\n")
    (tmp_path / "pipeline").mkdir()
    (tmp_path / "pipeline" / "allowlist.txt").write_text("")
    monkeypatch.chdir(tmp_path)
    english = Store(data, english=True)
    english.save(
        "ui",
        [
            _en("ACCEPT", "text", "Accept"),
            _en("ERR_JOINED", "text", "%s has joined."),
            _en("ERR_LEFT", "text", "%s has left."),
            _en("OKAY", "text", "Okay"),
            _en("ERR_GONE", "text", "%s is gone."),
        ],
    )
    english.save(
        "spell",
        [
            _en(100, "name", "Charge"),
            _en(100, "description", "Charge an enemy, dealing $s1 damage."),
            _en(101, "description", "Charge an enemy, dealing $s1 damage."),
            _en(102, "description", "Stuns the target for $d and deals $s1 damage."),
            _en(102, "aura", "Stunned."),
            _en(103, "description", "Deals $s1 damage."),
            _en(104, "description", "Heals for $s1$?s12345[ and more][]."),
            _en(200, "description", "Forever wording $s1."),
        ],
    )
    english.save(
        "item",
        [
            _en(117, "name", "Tough Jerky"),
            _en(117, "description", "Tough and chewy."),
            # an item with a Use: effect: its Forever English is the effect's text, then the flavour
            _en(118, "description", "Use: Restores health.\nRetail flavour."),
        ],
    )
    return data


def _run(data: Path, tmp_path: Path):
    return run_official(FIXTURES, data, BUILD, DATE, placeholders_out=tmp_path / "pipeline" / "names.tsv",
                        ambiguous_out=tmp_path / "pipeline" / "ui_ambiguous.tsv")


def _lines(data: Path, type_: str) -> dict:
    return {(ln["id"], ln["field"]): ln for ln in Store(data).load(type_)}


def test_ui_accepts_the_same_english_with_the_same_specifiers(tmp_path, monkeypatch):
    data = _setup(tmp_path, monkeypatch)
    report = _run(data, tmp_path)
    ui = _lines(data, "ui")
    assert ui[("ACCEPT", "text")]["it"] == "Accetta"
    assert ui[("ERR_JOINED", "text")]["it"] == "%s è entrato."
    assert ui[("ERR_GONE", "text")]["it"] == "%s non c'è più."
    line = ui[("ACCEPT", "text")]
    assert line["status"] == "pending"
    assert line["provenance"] == {"class": "official", "source": f"wago-itit@{BUILD}", "imported": DATE}
    assert validate_line("ui", line) == []
    # Review Focus 1: `%d` where the English has `%s` would break string.format → never imported
    assert ("ERR_LEFT", "text") not in ui
    assert report.counts["ui"]["accepted"] == 3
    assert report.counts["ui"]["rejected_specifiers"] == 1
    # the same text in both locales has nothing to translate; a key Forever lacks is not looked at
    assert ("OKAY", "text") not in ui
    assert report.counts["ui"]["same_as_english"] == 1


def test_ui_ships_no_italian_for_an_ambiguous_english_and_keeps_adjacent_arguments_in_order(
    tmp_path, monkeypatch
):
    # The addon finds a UI string by its English, so keys sharing one English must ship one Italian
    # (validate's ambiguity rule). When their Italian differs (`All` → `Tutto` / `Tutti`: gender and number
    # the English does not carry) none is imported, the group stays English, and every key is written to the
    # review file for a ruling. A group whose keys all share one Italian ships. Two free-text arguments the
    # English separates only by a space must keep their order (validate's adjacent_captures_reordered).
    data = _setup(tmp_path, monkeypatch)
    english = Store(data, english=True)
    extra = [("ALL_A", "All"), ("ALL_B", "All"), ("ALL_C", "All"), ("BOTH_A", "Both"), ("BOTH_B", "Both"),
             ("CANCEL_A", "Cancel"), ("CANCEL_B", "Cancel"), ("ERR_WELCOME", "Welcome %s %s")]
    english.save("ui", english.load("ui") + [_en(k, "text", en) for k, en in extra])
    report = _run(data, tmp_path)
    ui = _lines(data, "ui")
    for key in ("ALL_A", "ALL_B", "ALL_C", "BOTH_A", "BOTH_B", "ERR_WELCOME"):
        assert (key, "text") not in ui, key
    assert ui[("CANCEL_A", "text")]["it"] == ui[("CANCEL_B", "text")]["it"] == "Annulla"
    c = report.counts["ui"]
    assert (c["accepted"], c["rejected_ambiguous"], c["rejected_order"]) == (5, 5, 1)
    review = (tmp_path / "pipeline" / "ui_ambiguous.tsv").read_text(encoding="utf-8").splitlines()
    assert review == [
        "english\tkey\titalian",
        "All\tALL_A\tTutto",
        "All\tALL_B\tTutti",
        "All\tALL_C\tTutti",
        "Both\tBOTH_A\tEntrambi",
        "Both\tBOTH_B\tEntrambe",
    ]


def test_spell_slots_are_converted_like_a_draft_and_mismatches_rejected(tmp_path, monkeypatch):
    data = _setup(tmp_path, monkeypatch)
    report = _run(data, tmp_path)
    spell = _lines(data, "spell")
    assert spell[(100, "description")]["it"] == "Carica un nemico, infliggendo $N1 danni."
    # `$d` is the client's duration (its unit too): `$D<j>`; the value after it keeps its reading-order index
    assert spell[(102, "description")]["it"] == "Infligge $N2 danni e stordisce il bersaglio per $D1."
    assert spell[(102, "aura")]["it"] == "Stordito."
    # Review Focus 3: the Italian drops `$s1`, or shows another code than the English → never imported
    assert (101, "description") not in spell
    assert (103, "description") not in spell
    # retail English worded differently from Forever's: another text, never matched by id alone
    assert (200, "description") not in spell
    c = report.counts["spell"]
    assert (c["accepted"], c["rejected_slots"], c["rejected_english_mismatch"]) == (3, 2, 1)
    # a conditional template has no fixed slot count: not converted
    assert (104, "description") not in spell
    assert c["rejected_uncountable"] == 1


def test_item_flavour_only_where_forever_shows_only_the_flavour(tmp_path, monkeypatch):
    data = _setup(tmp_path, monkeypatch)
    report = _run(data, tmp_path)
    item = _lines(data, "item")
    assert item[(117, "description")]["it"] == "Dura e gommosa."
    assert (118, "description") not in item
    assert report.counts["item"]["accepted"] == 1
    assert report.counts["item"]["rejected_english_mismatch"] == 1


@pytest.mark.parametrize(
    "en, it, want",
    [
        ("Deals $s1 damage.", "Infligge $s1 danni.", "Infligge $N1 danni."),
        ("Deals $s1 and $s2.", "Infligge $s2 e $s1.", "Infligge $N2 e $N1."),
        ("Lasts $d.", "Dura $d.", "Dura $D1."),
        ("Absorbs ${$s1*2} damage for 10 sec.", "Assorbe ${$s1*2} danni per 10 s.", "Assorbe $N1 danni per 10 s."),
        ("Counter $1997w.", "Contatore $1997w.", "Contatore $1997w."),
        # an old tooltip's two spaces after a full stop are not a paragraph Blizzard's Italian must mirror
        ("Heals $o1 over $d.  Usable only here.", "Cura $o1 in $d. Utilizzabile solo qui.",
         "Cura $N1 in $D1. Utilizzabile solo qui."),
        ("Restores $26260o1 health over $26260d.", "Rigenera $26260o1 salute in $26260d.",
         "Rigenera $N1 salute in $D1."),
    ],
)
def test_convert_template(en, it, want):
    assert convert_template(en, it) == (want, None)


@pytest.mark.parametrize(
    "en, it, reason",
    [
        ("Deals $s1 damage.", "Infligge danni.", "slots"),
        ("Deals $s1 damage.", "Infligge $s1 $s1 danni.", "slots"),
        ("Deals $s1 damage.", "Infligge $o1 danni.", "slots"),
        ("Deals 5 damage.", "Infligge 6 danni.", "slots"),
        ("Lasts $d.", "Dura $d $lsecondo:secondi;.", "slots"),
        ("Heals $s1$?s1[ more][].", "Cura $s1$?s1[ altro][].", "uncountable"),
        ("Copies $@spelldesc123.", "Copia $@spelldesc123.", "uncountable"),
    ],
)
def test_convert_template_refuses(en, it, reason):
    assert convert_template(en, it) == (None, reason)


def test_official_wins_over_a_machine_draft_after_check(tmp_path, monkeypatch):
    data = _setup(tmp_path, monkeypatch)
    machine = {"class": "machine", "model": "m-1", "source": "draft-x-sg1@2026-10-01", "imported": "2026-10-01"}
    Store(data).save("spell", [entry(100, "description", "Carica un nemico con $N1 danni.", prov=machine)])
    _run(data, tmp_path)
    assert check.run([]) == 0
    line = _lines(data, "spell")[(100, "description")]
    assert line["provenance"]["class"] == "official"
    assert line["it"] == "Carica un nemico, infliggendo $N1 danni."
    assert line["status"] == "unaligned"
    assert [c["provenance"]["class"] for c in line["conflicts"]] == ["machine"]


def test_reimport_replaces_its_own_variant_and_drops_one_no_longer_accepted(tmp_path, monkeypatch):
    data = _setup(tmp_path, monkeypatch)
    _run(data, tmp_path)
    machine = {"class": "machine", "model": "m-1", "source": "draft-x-sg1@2026-10-01", "imported": "2026-10-01"}
    lines = Store(data).load("ui")
    for ln in lines:
        if ln["id"] == "ACCEPT":
            ln["conflicts"].append({"it": "Accetto", "provenance": machine})
    Store(data).save("ui", lines)
    # Forever's English for ACCEPT changes: the official text no longer matches and goes; the draft stays
    english = Store(data, english=True)
    english.save("ui", [ln if ln["id"] != "ACCEPT" else _en("ACCEPT", "text", "Accept!") for ln in english.load("ui")])
    report = run_official(FIXTURES, data, "12.1.5.70448", "2026-10-22", placeholders_out=tmp_path / "n.tsv")
    ui = _lines(data, "ui")
    assert ui[("ACCEPT", "text")]["it"] == "Accetto"
    assert ui[("ACCEPT", "text")]["conflicts"] == []
    assert ui[("ERR_JOINED", "text")]["provenance"]["imported"] == "2026-10-22"
    assert ui[("ERR_JOINED", "text")]["conflicts"] == []
    assert report.counts["ui"]["rejected_english_mismatch"] == 1


def test_placeholder_names_come_from_the_official_class_and_race_tables(tmp_path, monkeypatch):
    data = _setup(tmp_path, monkeypatch)
    out = tmp_path / "pipeline" / "names.tsv"
    _run(data, tmp_path)
    names = placeholders.read_names(out)
    assert names["CLASS"]["PRIEST"] == ("Sacerdote", "Sacerdotessa")
    assert names["CLASS"]["WARLOCK"] == ("Stregone", "Strega")
    assert names["RACE"]["NightElf"] == ("Elfo della Notte", "Elfa della Notte")
    # no female form in the table: the male one; a token on two rows takes the lowest id (Human, not Gilnean)
    assert names["RACE"]["Tauren"] == ("Tauren", "Tauren")
    assert names["RACE"]["Human"] == ("Umano", "Umana")
    lua = lua_writer.placeholders_text(names, "pipeline/placeholder_names.tsv")
    assert 'PRIEST = { m = "Sacerdote", f = "Sacerdotessa" }' in lua


def test_the_committed_names_are_the_official_ones():
    # the shipped table is the file `wfj import official` writes, read by generate
    assert placeholders.read_names(placeholders.NAMES_FILE) == placeholders.PLACEHOLDER_NAMES
    assert placeholders.PLACEHOLDER_NAMES["CLASS"]["PRIEST"] == ("Sacerdote", "Sacerdotessa")
    assert placeholders.PLACEHOLDER_NAMES["RACE"]["NightElf"] == ("Elfo della Notte", "Elfa della Notte")


def test_cli_refuses_an_unstamped_folder(tmp_path, monkeypatch, capsys):
    data = _setup(tmp_path, monkeypatch)
    folder = tmp_path / "retail"
    shutil.copytree(FIXTURES, folder)
    (folder / "tables-source.txt").unlink()
    assert import_run(["official", str(folder), "--build", BUILD, "--date", DATE]) == 1
    assert "no source stamp" in capsys.readouterr().err
    assert Store(data).load("ui") == []


def test_retail_reader_pairs_both_locales():
    en, it = retail.read_pair(FIXTURES, "GlobalStrings", retail.read_global_strings)
    assert en["ACCEPT"] == "Accept" and it["ACCEPT"] == "Accetta"


def test_official_descriptions_get_the_glossary_names_their_english_holds_marked(tmp_path, monkeypatch):
    # spec §8: Blizzard's own Italian is marked like a draft: the English decides which terms apply
    data = _setup(tmp_path, monkeypatch)
    (tmp_path / "pipeline" / "glossario_ufficiale.tsv").write_text(
        "tipo\tid\ten\tit\noggetto\t9\tTough\tDura\nzona\t1\tChewy Hills\tgommosa\n", encoding="utf-8")
    _run(data, tmp_path)
    item = _lines(data, "item")
    # "Chewy Hills" is not in the English, so its Italian form stays as Blizzard wrote it
    assert item[(117, "description")]["it"] == "⟦Tough=Dura⟧ e gommosa."
    _run(data, tmp_path)  # a re-import is the same text
    assert item[(117, "description")]["it"] == _lines(data, "item")[(117, "description")]["it"]
    assert _lines(data, "item")[(117, "description")]["conflicts"] == []
    # UI strings are interface text: never marked
    assert "⟦" not in "".join(ln["it"] for ln in Store(data).load("ui"))
