"""wfj voice pack: the addon OldpZ_ForeverITA_Voce and its zip, from a fixture store of tiny fake MP3s."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from test_voice_make import FakeEngine, _gen, world, write_quests  # noqa: F401 - world is a fixture

from wfj.cmd import voice, voice_ship
from wfj.core import voice_packs
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


def test_the_verb_is_reached_through_wfj_voice(made, monkeypatch):
    monkeypatch.setattr(voice_ship, "data_root", lambda: made.data)  # the fixture world, not the repo data
    assert voice.run(["pack", "--scope", "tirisfal", "--store", str(made.store), "--out", str(made.out),
                      "--config", str(made.config)]) == 0


def test_register_text_with_a_mixed_creature_and_a_female_other_voice():
    lines = {"g-1": Entry("g-1.mp3", "a" * 16, 1.25, ("g-1_f.mp3", 1.5),
                          {"x": ("g-1_x.mp3", 2.0, ("g-1_x_f.mp3", 2.5))})}
    lua = voice_pack.register_text(lines, {7: ("a", "b"), 3: "c"})
    assert '["g-1"] = { "g-1.mp3", "aaaaaaaaaaaaaaaa", 1.2, f = { "g-1_f.mp3", 1.5 }, v = { ["x"] = '\
        '{ "g-1_x.mp3", 2.0, f = { "g-1_x_f.mp3", 2.5 } } } },' in lua
    assert lua.index("[3] =") < lua.index('[7] = { m = "a", f = "b" },')


# ---- packs by level band (pipeline/voice-packs.toml) -----------------------------------------------------

PACKS = """
[[pack]]
suffix = "01_10"
title = "livelli 1-10"
levels = [1, 10]

[[pack]]
suffix = "11_20"
title = "livelli 11-20"
levels = [11, 20]

[[pack]]
suffix = "21_60"
title = "livelli 21-60"
levels = [21, 60]

[[pack]]
suffix = "Altro"
title = "libri, dialoghi e missioni senza livello"
other = true
"""
# 456 has its own level, 457 only the level it is offered at, 459 none (a quest pfQuest lacks)
LEVELS = "id\tmin\tlvl\tfonte\n456\t1\t3\tpfquest@x\n457\t12\t\tpfquest@x\n459\t\t\tassente\n"
ADDON_FOLDER = re.compile(r"^[A-Za-z0-9_]+$")  # Core/Voice.lua: tbl.folder:match("^[%w_]+$")


@pytest.fixture
def split(made):
    (made.tmp / "pipeline" / "voice-packs.toml").write_text(PACKS, encoding="utf-8")
    (made.tmp / "pipeline" / "quest_levels.tsv").write_text(LEVELS, encoding="utf-8")
    return made


def folder_files(w, folder: str) -> set[str]:
    return {p.name for p in (w.out / folder / "Sound").iterdir()}


def test_a_line_goes_to_the_band_of_its_quest_level_else_to_the_other_pack():
    packs = voice_packs.parse_packs(PACKS)
    levels = voice_packs.parse_levels(LEVELS + "600\t70\t\tpfquest@x\n700\t0\t0\tpfquest@x\n")
    assert levels == {456: 3, 457: 12, 600: 70, 700: 0}

    def of(key: str) -> str:
        return voice_packs.pack_of(key, packs, levels).suffix

    assert of("456-description") == "01_10" and of("456-completion") == "01_10"
    assert of("457-progress") == "11_20"  # no `lvl`: its `min`
    assert of("459-description") == "Altro"  # `assente`
    assert of("999-description") == "Altro"  # not in the table
    assert of("g-006921c124c689f8") == "Altro" and of("b-0105829b41883dcf") == "Altro"
    assert of("600-description") == "21_60" and of("700-description") == "01_10"  # past the ends: the end bands
    assert [p.folder for p in packs][-1] == "OldpZ_ForeverITA_Voce_Altro"


@pytest.mark.parametrize(("change", "why"), [
    (('suffix = "01_10"', 'suffix = "01-10"'), "suffix"),  # the addon refuses a '-' in a folder name
    (('levels = [11, 20]', 'levels = [12, 20]'), "gap"),
    (('levels = [11, 20]', 'levels = [10, 20]'), "overlap"),
    (('levels = [21, 60]', 'levels = [60, 21]'), "levels"),
    (('levels = [21, 60]', 'other = true'), "exactly one"),
    (('other = true', 'levels = [61, 99]'), "exactly one"),
    (('suffix = "21_60"', 'suffix = "11_20"'), "twice"),
    (('title = "livelli 1-10"', 'title = ""'), "title"),
])
def test_a_bad_pack_table_is_refused(change, why):
    with pytest.raises(ValueError, match=why):
        voice_packs.parse_packs(PACKS.replace(*change))


def test_the_committed_pack_table_is_valid_and_every_folder_is_one_the_addon_accepts():
    pipeline = Path(__file__).resolve().parents[2] / "pipeline"
    packs = voice_packs.parse_packs((pipeline / "voice-packs.toml").read_text(encoding="utf-8"))
    for p in packs:
        assert ADDON_FOLDER.match(p.folder) and p.folder.startswith(voice_pack.FOLDER)
    levels = voice_packs.parse_levels((pipeline / "quest_levels.tsv").read_text(encoding="utf-8"))
    assert levels and all(voice_packs.pack_of(f"{q}-description", packs, levels).levels for q in levels)


def test_pack_all_builds_each_band_with_its_own_lines_title_and_zip(split, capsys):
    assert pack(split, "--pack", "all") == 0
    out = capsys.readouterr().out
    low, mid, other = (f"OldpZ_ForeverITA_Voce_{s}" for s in ("01_10", "11_20", "Altro"))
    assert folder_files(split, low) == {"456-completion.mp3", "456-description.mp3", "456-description_f.mp3"}
    assert folder_files(split, mid) == {"457-description.mp3"}
    assert folder_files(split, other) == {"459-description.mp3", "459-description_um.mp3"}
    # a band with no line of the scope is not built
    assert "OldpZ_ForeverITA_Voce_21_60: no line of scope tirisfal, not built" in out
    assert not (split.out / "OldpZ_ForeverITA_Voce_21_60").exists()
    assert not (split.out / "OldpZ_ForeverITA_Voce").exists()
    for folder in (low, mid, other):
        z = split.out.parent / f"{folder}-2026-10-24.zip"
        assert voice_ship.check_zip(z, sorted(folder_files(split, folder)), folder) == []
        assert {n.split("/")[0] for n in zipfile.ZipFile(z).namelist()} == {folder}
        assert f'folder = "{folder}",' in (split.out / folder / "Register.lua").read_text(encoding="utf-8")
    toc = (split.out / mid / f"{mid}.toc").read_text(encoding="utf-8")
    assert "## Title: oLd_pZ Forever - Voci italiane (livelli 11-20)" in toc.splitlines()
    readme = (split.out / mid / "LEGGIMI.txt").read_text(encoding="utf-8")
    assert readme.startswith("oLd_pZ Forever - Voci italiane (livelli 11-20)") and mid in readme
    assert "1 battute" in readme
    # the creature cast to another voice travels with the line that needs it
    assert "[2079]" in register_of(split, other) and "[2079]" not in register_of(split, low)
    assert f"voice pack: {low}: 2 lines, 3 files" in out


def register_of(w, folder: str) -> str:
    return (w.out / folder / "Register.lua").read_text(encoding="utf-8")


def test_pack_name_builds_only_that_pack_by_suffix_or_folder(split):
    assert pack(split, "--pack", "11_20") == 0
    assert [p.name for p in split.out.iterdir()] == ["OldpZ_ForeverITA_Voce_11_20"]
    shutil.rmtree(split.out)
    assert pack(split, "--pack", "OldpZ_ForeverITA_Voce_Altro") == 0
    assert [p.name for p in split.out.iterdir()] == ["OldpZ_ForeverITA_Voce_Altro"]


def test_an_unknown_pack_is_refused(split, capsys):
    assert pack(split, "--pack", "61_70") == 1
    assert "no voice pack '61_70'" in capsys.readouterr().err
    assert not split.out.exists()


def test_one_pack_over_420_mb_writes_none(split, monkeypatch, capsys):
    def size(*stems: str) -> int:
        return sum((split.store / "mp3" / f"{s}.mp3").stat().st_size for s in stems)

    other = size("459-description", "459-description_um")
    low = size("456-completion", "456-description", "456-description_f")
    assert low > other  # only the first band is over
    monkeypatch.setattr(voice_ship, "LIMIT", other)
    assert pack(split, "--pack", "all") == 1
    err = capsys.readouterr().err
    assert "OldpZ_ForeverITA_Voce_01_10:" in err and "Altro" not in err and "nothing written" in err
    assert not split.out.exists()


PREFIXED = PACKS.replace('levels = [1, 10]', 'levels = [1, 10]\nprefixes = ["i-"]') + """
[[pack]]
suffix = "Chat"
title = "frasi dei PNG in chat"
prefixes = ["s-"]
"""


def test_a_prefixed_key_goes_to_its_pack_before_the_levels():
    packs = voice_packs.parse_packs(PREFIXED)
    levels = voice_packs.parse_levels(LEVELS)

    def of(key: str) -> str:
        return voice_packs.pack_of(key, packs, levels).suffix

    assert of("s-006921c124c689f8") == "Chat"
    assert of("i-316345") == "01_10"
    assert of("g-006921c124c689f8") == "Altro"
    assert of("457-progress") == "11_20"
    chat = voice_packs.find(packs, "Chat")
    assert chat.prefixes == ("s-",) and chat.levels is None and not chat.other


@pytest.mark.parametrize(("change", "why"), [
    (('prefixes = ["s-"]', 'prefixes = ["i-"]'), "prefix"),  # one prefix, two packs
    (('prefixes = ["s-"]', 'prefixes = []'), "want levels"),  # a pack with no band, no other, no prefix
    (('prefixes = ["s-"]', 'prefixes = ["s"]'), "prefix"),  # a prefix is letters then '-'
])
def test_a_bad_prefix_is_refused(change, why):
    with pytest.raises(ValueError, match=why):
        voice_packs.parse_packs(PREFIXED.replace(*change))


def test_the_committed_table_sends_chat_greetings_and_intros_to_their_packs():
    pipeline = Path(__file__).resolve().parents[2] / "pipeline"
    packs = voice_packs.parse_packs((pipeline / "voice-packs.toml").read_text(encoding="utf-8"))
    assert voice_packs.pack_of("s-0123456789abcdef", packs, {}).suffix == "Chat"
    assert voice_packs.pack_of("i-316345", packs, {}).suffix == "01_20"
    # greetings ride with the chat lines: with them Altro is over the limit
    assert voice_packs.pack_of("g-0123456789abcdef", packs, {}).suffix == "Chat"
    assert voice_packs.pack_of("n-genorcm1-g1", packs, {}).suffix == "Chat"


def test_the_pack_of_the_greetings_names_who_greets_and_the_english_files_to_silence():
    lines = {"n-um-g1": Entry("n-um-g1.mp3", "a" * 16, 0.8)}
    lua = voice_pack.register_text(lines, {}, hello=({2079: "um", 1992: "uf"}, [700, 701]))
    assert "  greeters = {\n    [1992] = \"uf\",\n    [2079] = \"um\",\n  }," in lua
    assert "  hellomute = { 700, 701 }," in lua
    assert "greeters" not in voice_pack.register_text(lines, {})  # a pack without greetings says nothing


def test_the_chat_pack_carries_the_greetings_of_its_voices_only(world):  # noqa: F811 - the fixture
    vf_rows = [{"key": "n-um-g1", "voice": "um", "speaker": 2079, "it": "Che vuoi?"}]
    (world.data / "voice" / "hello.jsonl").write_text(
        "".join(__import__("json").dumps(r) + "\n" for r in vf_rows), encoding="utf-8")
    (world.data / "voice" / "greeters.jsonl").write_text(
        '{"creature": 2079, "voice": "um"}\n{"creature": 9, "voice": "nobody"}\n', encoding="utf-8")
    (world.tmp / "pipeline").mkdir(exist_ok=True)
    (world.tmp / "pipeline" / "voice_hello_mute.txt").write_text("# files\n700\n701\n", encoding="utf-8")
    assert voice_ship.hello_of(world.data, {"n-um-g1": Entry("n-um-g1.mp3", "a" * 16, 0.8)}) == (
        {2079: "um"}, [700, 701])
    assert voice_ship.hello_of(world.data, {"1-description": Entry("x.mp3", "a" * 16, 1.0)}) is None


def test_a_line_in_chat_carries_the_english_files_it_silences():
    lines = {"s-00112233445566ff": Entry("s-00112233445566ff.mp3", "a" * 16, 2.0, mute=(555001, 555002)),
             "g-00112233445566ff": Entry("g-00112233445566ff.mp3", "b" * 16, 1.0)}
    lua = voice_pack.register_text(lines, {})
    assert '["s-00112233445566ff"] = { "s-00112233445566ff.mp3", "' + "a" * 16 + '", 2.0, m = { 555001, 555002 } },' \
        in lua
    assert "m = " not in lua.split('["g-00112233445566ff"]')[1].split("\n")[0]


def test_the_mute_table_reaches_only_the_lines_in_chat(tmp_path):
    table = tmp_path / "voice_mute.tsv"
    table.write_text("key\tfiles\n00112233445566ff\t555001,555002\n", encoding="utf-8")
    lines = {"s-00112233445566ff": Entry("s.mp3", "a" * 16, 2.0), "g-00112233445566ff": Entry("g.mp3", "b" * 16, 1.0)}
    voice_ship.add_mutes(lines, voice_ship.read_mutes(table))
    assert lines["s-00112233445566ff"].mute == (555001, 555002)
    assert lines["g-00112233445566ff"].mute == ()
    assert voice_ship.read_mutes(tmp_path / "absent.tsv") == {}


def test_the_mute_table_is_made_from_the_server_sounds_and_the_client_sound_kits():
    from wfj.core.voice import gossip_id
    from wfj.dev import voice_mute

    got = voice_mute.rows({"Release the hounds!": 61, "No sound kit.": 9}, {61: [567437, 567438], 63: [1]})
    assert got == {gossip_id("Release the hounds!"): [567437, 567438]}
