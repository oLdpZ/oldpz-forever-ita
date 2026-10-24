"""wfj voice pack: the addon OldpZ_ForeverITA_Voce and its zip, from a fixture store of tiny fake MP3s."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile

import pytest
from test_voice_make import FakeEngine, _gen, world, write_quests  # noqa: F401 - world is a fixture

from wfj.cmd import voice, voice_ship
from wfj.emit import voice_pack
from wfj.emit.voice_pack import Entry

TOC = "## Interface: 16001\n## Title: oLd_pZ Forever - Traduzione Italiana\n\nCore\\Const.lua\n"
NAME = re.compile(r"^[\w\-]+\.mp3$")


@pytest.fixture
def made(world):  # noqa: F811 - the fixture of test_voice_make
    """The scope's audio made (456-description also for a female character, 459-description by two voices)."""
    addon = world.tmp / "addon" / "OldpZ_ForeverITA"
    addon.mkdir(parents=True)
    (addon / "OldpZ_ForeverITA.toc").write_text(TOC, encoding="utf-8")
    speakers = world.data / "voice" / "speakers.jsonl"
    text = speakers.read_text(encoding="utf-8").replace(
        '"key": "459-description", "speaker": 1992', '"key": "459-description", "speaker": 1992, "others": [2079]'
    )
    speakers.write_text(text, encoding="utf-8")
    _gen(world, FakeEngine())
    world.out = world.tmp / "build" / "voice-pack"
    return world


def pack(w, *extra):
    return voice_ship.run(
        ["--scope", "tirisfal", "--store", str(w.store), "--out", str(w.out), "--version", "2026-10-24",
         "--config", str(w.config), *extra],
        root=w.data,
    )


def register(w) -> str:
    return (w.out / "OldpZ_ForeverITA_Voce" / "Register.lua").read_text(encoding="utf-8")


def test_the_zip_holds_only_the_files_register_lists(made, capsys):
    assert pack(made) == 0
    zpath = made.out.parent / "OldpZ_ForeverITA_Voce-2026-10-24.zip"
    names = zipfile.ZipFile(zpath).namelist()
    assert {n.split("/")[0] for n in names} == {"OldpZ_ForeverITA_Voce"}
    listed = set(re.findall(r'"([^"]+\.mp3)"', register(made)))
    sound = {n.removeprefix("OldpZ_ForeverITA_Voce/Sound/") for n in names if "/Sound/" in n}
    assert listed == sound and listed
    assert all(NAME.match(f) for f in sound)
    assert sorted(set(names) - {f"OldpZ_ForeverITA_Voce/Sound/{f}" for f in sound}) == [
        "OldpZ_ForeverITA_Voce/LEGGIMI.txt", "OldpZ_ForeverITA_Voce/OldpZ_ForeverITA_Voce.toc",
        "OldpZ_ForeverITA_Voce/Register.lua"]
    assert "MB" in capsys.readouterr().out  # the total size is printed


def test_the_register_call_has_the_format_3_shape(made):
    pack(made)
    lua = register(made)
    assert 'OldpZ_ForeverITA_Voce' in lua and "format = 3," in lua
    assert re.search(r'\["456-description"\] = \{ "456-description\.mp3", "[0-9a-f]{16}", 0\.5, '
                     r'f = \{ "456-description_f\.mp3", 0\.5 \} \},', lua)
    assert re.search(r'\["459-description"\] = \{ "459-description\.mp3", "[0-9a-f]{16}", 0\.5, '
                     r'v = \{ \["um"\] = \{ "459-description_um\.mp3", 0\.5 \} \} \},', lua)
    assert '[1992] = "uf",' in lua and '[2079] = "um",' in lua
    assert '["457-description"] = { "457-description.mp3"' in lua


def test_the_register_file_parses_as_lua_and_makes_the_call(made, tmp_path):
    lua = shutil.which("lua") or shutil.which("luajit")
    if lua is None:
        pytest.skip("no Lua interpreter")
    pack(made)
    probe = (
        "local got; function OldpZ_ForeverITA_RegisterVoice(t) got = t end "
        f"dofile('{made.out / 'OldpZ_ForeverITA_Voce' / 'Register.lua'}') "
        "assert(got.format == 3 and got.folder == 'OldpZ_ForeverITA_Voce') "
        "assert(got.lines['456-description'].f[1] == '456-description_f.mp3') "
        "assert(got.lines['459-description'].v.um[2] == 0.5) assert(got.creatures[2079] == 'um')"
    )
    done = subprocess.run([lua, "-e", probe], check=False, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_the_toc_copies_the_interface_of_the_main_addon(made):
    (made.tmp / "addon" / "OldpZ_ForeverITA" / "OldpZ_ForeverITA.toc").write_text(
        TOC.replace("16001", "16002"), encoding="utf-8")
    pack(made)
    toc = (made.out / "OldpZ_ForeverITA_Voce" / "OldpZ_ForeverITA_Voce.toc").read_text(encoding="utf-8")
    assert toc.splitlines()[:7] == [
        "## Interface: 16002",
        "## Title: oLd_pZ Forever - Voci italiane",
        toc.splitlines()[2],
        "## IconTexture: Interface\\AddOns\\OldpZ_ForeverITA\\Media\\icon",
        "## Dependencies: OldpZ_ForeverITA",
        "## Author: oLd_pZ",
        "## Version: 2026-10-24",
    ]
    assert toc.rstrip().endswith("Register.lua")
    readme = (made.out / "OldpZ_ForeverITA_Voce" / "LEGGIMI.txt").read_text(encoding="utf-8")
    assert "Gemini" in readme and "OldpZ_ForeverITA" in readme and "4 battute" in readme


def test_a_stale_line_is_left_out_and_listed(made, capsys):
    write_quests(made.data, **{"457_description": "Uccidi $N1 lupi, presto."})
    assert pack(made) == 0
    out = capsys.readouterr().out
    assert "left out, stale: 1" in out and "left out: 457-description: stale" in out
    assert "457-description" not in register(made)
    assert not (made.out / "OldpZ_ForeverITA_Voce" / "Sound" / "457-description.mp3").exists()


def test_a_missing_or_damaged_take_is_left_out(made, capsys):
    (made.store / "mp3" / "459-description.mp3").write_bytes(b"MP3 other")
    (made.store / "mp3" / "456-completion.mp3").unlink()
    pack(made)
    out = capsys.readouterr().out
    assert "456-completion: damaged" in out and "459-description: damaged" in out
    # the other voice's take has no main take to hang on
    assert "459-description_um: incomplete" in out
    lua = register(made)
    assert "459-description" not in lua and "456-completion" not in lua


def test_a_female_take_without_its_male_one_is_left_out(made, capsys):
    (made.store / "mp3" / "456-description.mp3").write_bytes(b"MP3 other")
    pack(made)
    assert "456-description_f: incomplete" in capsys.readouterr().out
    assert "456-description" not in register(made)


def test_a_left_out_other_voice_leaves_out_the_whole_line(made, capsys):
    # shipped alone, the main take would speak for the creature cast to the other voice: one NPC, two voices
    (made.store / "mp3" / "459-description_um.mp3").write_bytes(b"MP3 other")
    pack(made)
    out = capsys.readouterr().out
    assert "459-description_um: damaged" in out and "459-description: incomplete" in out
    assert "left out, incomplete: 1" in out
    assert "459-description" not in register(made)
    assert not (made.out / "OldpZ_ForeverITA_Voce" / "Sound" / "459-description.mp3").exists()


def test_a_left_out_female_take_leaves_out_the_whole_line(made, capsys):
    # shipped alone, the male take would call a female character "eroe"
    (made.store / "mp3" / "456-description_f.mp3").write_bytes(b"MP3 other")
    pack(made)
    out = capsys.readouterr().out
    assert "456-description_f: damaged" in out and "456-description: incomplete" in out
    assert "456-description" not in register(made)


def test_over_420_mb_fails_and_writes_nothing(made, monkeypatch, capsys):
    monkeypatch.setattr(voice_ship, "LIMIT", 10)
    assert pack(made) == 1
    err = capsys.readouterr()
    assert "MB is over the" in err.err
    assert "MB" in err.out
    assert not made.out.exists()


def test_the_verb_is_reached_through_wfj_voice(made):
    assert voice.run(["pack", "--scope", "tirisfal", "--store", str(made.store), "--out", str(made.out),
                      "--config", str(made.config)]) == 0


def test_register_text_with_a_mixed_creature_and_a_female_other_voice():
    lines = {"g-1": Entry("g-1.mp3", "a" * 16, 1.25, ("g-1_f.mp3", 1.5),
                          {"x": ("g-1_x.mp3", 2.0, ("g-1_x_f.mp3", 2.5))})}
    lua = voice_pack.register_text(lines, {7: ("a", "b"), 3: "c"})
    assert '["g-1"] = { "g-1.mp3", "aaaaaaaaaaaaaaaa", 1.2, f = { "g-1_f.mp3", 1.5 }, v = { ["x"] = '\
        '{ "g-1_x.mp3", 2.0, f = { "g-1_x_f.mp3", 2.5 } } } },' in lua
    assert lua.index("[3] =") < lua.index('[7] = { m = "a", f = "b" },')
