"""wfj package-check: the release zip holds exactly the shipped files (docs/operations/release.md)."""

import zipfile
from pathlib import Path

import pytest

from wfj.cmd import package_check

TRACKED = [
    "addon/OldpZ_ForeverITA/OldpZ_ForeverITA.toc",
    "addon/OldpZ_ForeverITA/Main.lua",
    "addon/OldpZ_ForeverITA/Core/Const.lua",
    "addon/OldpZ_ForeverITA/Fonts/ipagui.ttf",
    "LICENSE",
    "ATTRIBUTION.md",
    "addon/OldpZ_ForeverITA/Data/Quest/.gitkeep",  # tracked, but a dotfile: never shipped
    "README.md",  # tracked, but not shipped
    "pipeline/wfj/cli.py",
]

TOC = """## Interface: 16001
## Title: oLd_pZ Forever - Traduzione Italiana
## Version: {version}
{project}{extra}
Core\\Const.lua
# a comment
Main.lua
"""


def make_zip(path: Path, *, version="v1.2.3", project="123456", extra="", drop=(), add=()) -> Path:
    files = {
        "OldpZ_ForeverITA/OldpZ_ForeverITA.toc": TOC.format(
            version=version, project="" if project is None else f"## X-Curse-Project-ID: {project}\n", extra=extra
        ),
        "OldpZ_ForeverITA/Main.lua": "-- main\n",
        "OldpZ_ForeverITA/Core/Const.lua": "-- const\n",
        "OldpZ_ForeverITA/Fonts/ipagui.ttf": "font",
        "OldpZ_ForeverITA/LICENSE": "GPL",
        "OldpZ_ForeverITA/ATTRIBUTION.md": "# Attribution\n",
    }
    for name in drop:
        del files[name]
    files.update({name: "x" for name in add})
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("OldpZ_ForeverITA/", "")  # directory entries, as the packager writes them
        for name, body in files.items():
            zf.writestr(name, body)
    return path


ALLOWED = package_check.allowed_files(TRACKED)


def check(tmp_path, **kw):
    return package_check.check(make_zip(tmp_path / "a.zip", **kw), "1.2.3", ALLOWED)


def test_allowed_set_is_the_addon_folder_plus_the_license_files():
    assert {
        "OldpZ_ForeverITA/OldpZ_ForeverITA.toc",
        "OldpZ_ForeverITA/Main.lua",
        "OldpZ_ForeverITA/Core/Const.lua",
        "OldpZ_ForeverITA/Fonts/ipagui.ttf",
        "OldpZ_ForeverITA/LICENSE",
        "OldpZ_ForeverITA/ATTRIBUTION.md",
    } == ALLOWED


def test_good_zip_passes(tmp_path):
    assert check(tmp_path) == []


@pytest.mark.parametrize(
    "name",
    ["OldpZ_ForeverITA/README.md", "OldpZ_ForeverITA/.DS_Store", "OldpZ_ForeverITA/.release-notes.md",
     "OldpZ_ForeverITA/pipeline/wfj/cli.py", "OldpZ_ForeverITA/CHANGELOG.md"],
)
def test_a_file_outside_the_allowed_set_fails(tmp_path, name):
    assert check(tmp_path, add=[name]) == [f"not a shipped file: {name}"]


def test_a_second_top_level_folder_fails(tmp_path):
    problems = check(tmp_path, add=["Other/Other.toc"])
    assert "top-level entry other than OldpZ_ForeverITA/: Other" in problems
    assert "not a shipped file: Other/Other.toc" in problems


def test_a_missing_file_fails_and_names_the_toc_entry(tmp_path):
    problems = check(tmp_path, drop=["OldpZ_ForeverITA/Core/Const.lua"])
    assert problems == [
        "missing from the zip: OldpZ_ForeverITA/Core/Const.lua",
        "the TOC lists a file the zip lacks: Core/Const.lua",
    ]


def test_missing_license_files_fail(tmp_path):
    problems = check(tmp_path, drop=["OldpZ_ForeverITA/LICENSE", "OldpZ_ForeverITA/ATTRIBUTION.md"])
    assert problems == [
        "missing from the zip: OldpZ_ForeverITA/ATTRIBUTION.md",
        "missing from the zip: OldpZ_ForeverITA/LICENSE",
    ]


def test_missing_toc_fails(tmp_path):
    problems = check(tmp_path, drop=["OldpZ_ForeverITA/OldpZ_ForeverITA.toc"])
    assert problems[-1] == "missing from the zip: OldpZ_ForeverITA/OldpZ_ForeverITA.toc"


@pytest.mark.parametrize("version", ["@project-version@", "v1.2.4", "1.2.3", ""])
def test_wrong_version_fails(tmp_path, version):
    assert check(tmp_path, version=version) == [f"## Version is '{version}', expected 'v1.2.3'"]


@pytest.mark.parametrize("project", ["", "abc", "１２３"])
def test_project_id_must_be_a_number(tmp_path, project):
    assert check(tmp_path, project=project) == [
        f"## X-Curse-Project-ID is '{project}': fill in the CurseForge project id"
    ]


def test_project_id_may_be_absent(tmp_path):
    assert check(tmp_path, project=None) == []


@pytest.mark.parametrize("field", ["Dependencies", "RequiredDeps", "OptionalDeps", "Dep", "dependencies", "DEPS"])
def test_dependencies_fail(tmp_path, field):
    assert check(tmp_path, extra=f"## {field}: Ace3") == [f"## {field}: the addon never depends on another addon"]


def test_real_tracked_files_give_the_addon_folder(root):
    allowed = package_check.allowed_files(package_check.tracked_files(root))
    assert "OldpZ_ForeverITA/OldpZ_ForeverITA.toc" in allowed
    assert "OldpZ_ForeverITA/LICENSE" in allowed and "OldpZ_ForeverITA/ATTRIBUTION.md" in allowed
    assert all(name.startswith("OldpZ_ForeverITA/") for name in allowed)
    assert not any("/Data/" not in n and n.endswith((".py", ".jsonl")) for n in allowed)


def test_cli_rejects_a_malformed_version(tmp_path, capsys):
    assert package_check.run([str(make_zip(tmp_path / "a.zip")), "--version", "v1.2.3"]) == 1
    assert "is not a version" in capsys.readouterr().err


def test_an_addon_level_license_file_collides_with_the_root_one():
    with pytest.raises(package_check.ReleaseError, match="collides with the root LICENSE"):
        package_check.allowed_files([*TRACKED, "addon/OldpZ_ForeverITA/LICENSE"])


def test_every_top_level_file_ships_or_is_ignored(root):
    """A new top-level file must be listed: shipped (LICENSE, ATTRIBUTION.md) or in .pkgmeta's ignore list.
    Otherwise the packager copies it into the zip and the package check refuses the release."""
    import subprocess

    from wfj.cmd.package_check import ROOT_FILES

    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()
    top = {p.split("/", 1)[0] for p in tracked if not p.startswith(".")}
    meta = (root / ".pkgmeta").read_text(encoding="utf-8")
    ignored = set(meta.split("ignore:", 1)[1].split()) - {"-"}
    unlisted = sorted(top - set(ROOT_FILES) - ignored - {"addon"})
    assert unlisted == [], f"add to .pkgmeta ignore (or ship): {unlisted}"
