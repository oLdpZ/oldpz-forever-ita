"""Retail tables are fetched twice, once per locale (`<table>.enUS.csv`, `<table>.itIT.csv`): the stamp names
each locale file on its own line, and `check` refuses a folder where one of the files is missing."""

from pathlib import Path

import pytest

from wfj.dev import tables_stamp as stamp_cli
from wfj.io import tables_stamp

BUILD = "12.1.5.70448"


def _pair(folder: Path) -> tuple[Path, Path]:
    folder.mkdir(exist_ok=True)
    en = folder / "ItemSparse.enUS.csv"
    it = folder / "ItemSparse.itIT.csv"
    en.write_text('ID,Description_lang\n117,"Tough"\n', encoding="utf-8")
    it.write_text('ID,Description_lang\n117,"Dura"\n', encoding="utf-8")
    return en, it


def test_the_locale_suffix_is_part_of_the_table_name():
    assert tables_stamp.table_of(Path("x/ItemSparse.enUS.csv")) == "ItemSparse.enUS"
    assert tables_stamp.table_of(Path("x/ItemSparse.itIT.csv")) == "ItemSparse.itIT"
    # a non-locale suffix still names the plain table
    assert tables_stamp.table_of(Path("x/ItemSparse.excerpt.csv")) == "ItemSparse"
    assert tables_stamp.table_of(Path("x/ItemSparse.csv")) == "ItemSparse"


def test_check_accepts_both_locale_files_stamped(tmp_path):
    en, it = _pair(tmp_path / "retail")
    assert stamp_cli.main(["write", "--dir", str(tmp_path / "retail"), "--src", "wago", "--build", BUILD, "ItemSparse.enUS", "ItemSparse.itIT"]) == 0
    stamps = tables_stamp.read(tmp_path / "retail")
    assert stamps == {"ItemSparse.enUS": f"wago@{BUILD}", "ItemSparse.itIT": f"wago@{BUILD}"}
    tables_stamp.check([en, it], "wago", BUILD)
    assert stamp_cli.main(["check", "--src", "wago", "--build", BUILD, str(en), str(it)]) == 0


def test_check_refuses_a_missing_locale_file(tmp_path, capsys):
    en, it = _pair(tmp_path / "retail")
    tables_stamp.write(tmp_path / "retail", ["ItemSparse.enUS", "ItemSparse.itIT"], f"wago@{BUILD}")
    it.unlink()
    with pytest.raises(ValueError, match=r"ItemSparse\.itIT\.csv: no such file"):
        tables_stamp.check([en, it], "wago", BUILD)
    assert stamp_cli.main(["check", "--src", "wago", "--build", BUILD, str(en), str(it)]) == 1
    assert "no such file" in capsys.readouterr().err


def test_one_locale_stamp_does_not_cover_the_other(tmp_path):
    en, it = _pair(tmp_path / "retail")
    tables_stamp.write(tmp_path / "retail", ["ItemSparse.enUS"], f"wago@{BUILD}")
    with pytest.raises(ValueError, match=r"no source stamp for ItemSparse\.itIT"):
        tables_stamp.check([en, it], "wago", BUILD)
