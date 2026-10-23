"""Voice over text rules (`core/voice.py`): the Italian the addon ships becomes the text a voice reads. Pure."""

import pytest

from wfj.core import hashing, voice
from wfj.core.voice import (
    Job,
    VoiceError,
    book_key,
    fingerprint,
    gossip_key,
    in_step,
    it_hash,
    live_values,
    needs_spoken,
    needs_variants,
    quest_key,
    read_scope_file,
    speech_text,
    text_hash,
)


def test_names_are_spoken_in_italian():
    assert speech_text("Vai a ⟦Deathknell=Albamorta⟧.", "1-description", "m") == "Vai a Albamorta."


def test_player_name_is_hero_by_sex():
    assert speech_text("Ben fatto, {name}!", "1-completion", "m") == "Ben fatto, eroe!"
    assert speech_text("Ben fatto, {name}!", "1-completion", "f") == "Ben fatto, eroina!"


def test_gender_pairs_follow_sex():
    assert speech_text("Non sei più schiav<o/a>.", "1-description", "f") == "Non sei più schiava."
    assert speech_text("Non sei più schiav<o/a>.", "1-description", "m") == "Non sei più schiavo."
    assert speech_text("<Un/Una> eroe, <il/la> migliore.", "1-description", "f") == "Una eroe, la migliore."
    assert speech_text("Sei <eroe/eroina>, <ore/rice>.", "1-description", "f") == "Sei eroina, rice."


def test_class_needs_a_spoken_version():
    with pytest.raises(VoiceError):
        speech_text("Un vero {class}.", "1-description", "m")
    assert speech_text("Un vero {class}.", "1-description", "m", spoken="Un vero campione.") == "Un vero campione."
    with pytest.raises(VoiceError):
        speech_text("Che vuoi, {race}?", "1-description", "m")


def test_the_spoken_version_goes_through_the_same_rules():
    assert speech_text("Un {class}.", "1-description", "f", spoken="Una brava, {name}.") == "Una brava, eroina."


def test_variants_only_when_sex_changes_the_words():
    assert needs_variants("Ben fatto, {name}!") and needs_variants("schiav<o/a>")
    assert not needs_variants("Vai a ⟦Deathknell=Albamorta⟧.")
    assert not needs_variants("<sbuffa> Ancora tu?")
    assert not needs_variants('<IMG src="Interface\\Pictures\\x"/>Testo.')


def test_spoken_is_needed_for_class_and_race_only():
    assert needs_spoken("Un vero {class}.") and needs_spoken("Che vuoi, {race}?")
    assert not needs_spoken("Ben fatto, {name}!")


def test_hash_is_over_the_raw_text():
    assert it_hash("Vai a ⟦Deathknell=Albamorta⟧.") == hashing.key("Vai a ⟦Deathknell=Albamorta⟧.")


def test_stage_directions_and_markup_are_dropped():
    assert speech_text("<sbuffa> Ancora tu?$B$BVattene.", "g-0123456789abcdef", "m") == "Ancora tu?\n\nVattene."


def test_a_line_that_is_all_stage_direction_is_read_without_its_brackets():
    assert speech_text("<Trevan annuisce lentamente.>", "g-0123456789abcdef", "m") == "Trevan annuisce lentamente."
    text = "<In presenza della pietra, l'anima si agita.\n\nSembra che tu sia più vicin<o/a>.>"
    assert speech_text(text, "95883-completion", "f") == "In presenza della pietra, l'anima si agita.\n\nSembra che tu sia più vicina."


def test_html_tags_of_a_page_are_not_read():
    assert speech_text('<IMG src="x" align="left"/>Salve.', "b-0123456789abcdef", "m") == "Salve."


def test_colour_codes_and_the_entity_name_are_removed():
    assert speech_text("|cff33ccffTutte e quattro le torri|r cadono.", "g-0123456789abcdef", "m") == "Tutte e quattro le torri cadono."
    assert speech_text("%s comincia a battere più in fretta.", "g-0123456789abcdef", "m") == "comincia a battere più in fretta."


def test_numbers_are_filled_from_the_english_values():
    assert speech_text("Porta $N1  e $N2 vermi.", "1-description", "m", ("3", "5")) == "Porta 3 e 5 vermi."


def test_a_number_only_the_game_knows_reads_as_some():
    assert speech_text("Ne servono $N2.", "1-description", "m", ("3",)) == "Ne servono alcuni."
    assert speech_text("Ne abbiamo $2113w, su $2114W.", "g-0123456789abcdef", "m") == "Ne abbiamo alcuni, su alcuni."


def test_a_literal_percent_stays():
    assert speech_text("Ne sono certo al 100%!", "g-0123456789abcdef", "m") == "Ne sono certo al 100%!"


@pytest.mark.parametrize("it", ["Che {strano}.", "Un $x qualsiasi.", "Barra | qui.", "Un < da solo.", "Un > da solo."])
def test_other_markup_fails_with_the_key(it):
    with pytest.raises(VoiceError, match="7-description"):
        speech_text(it, "7-description", "m")


def test_nothing_left_to_read_fails():
    with pytest.raises(VoiceError, match="7-progress"):
        speech_text("%s", "7-progress", "m")


def test_live_values_follow_the_english_numbers():
    assert live_values("Bring me 5 Boar Ribs and 3 Crag Boar Hides.") == ["5", "3"]
    assert live_values("Slay 1,200 foes.") == ["1200"]
    assert live_values("Bring 2 to 4 hides.") == ["da 2 a 4"]
    assert live_values("Mk2 and 6.") == ["6"]


def test_keys():
    assert quest_key(456, "progress") == "456-progress"
    assert gossip_key("0123456789abcdef") == "g-0123456789abcdef"
    assert book_key("0123456789abcdef") == "b-0123456789abcdef"


def test_text_hash_pins_the_numbers_and_the_spoken_version():
    assert text_hash("Testo") == it_hash("Testo")
    assert text_hash("Testo", ("3",)) != text_hash("Testo")
    assert text_hash("Testo", spoken="Detto") not in (text_hash("Testo"), text_hash("Testo", ("3",)))


def test_fingerprint_changes_with_each_ingredient():
    base = ("h", "m1", "Charon", "gemini-3.1-flash-tts-preview", "nota", "m")
    assert fingerprint(*base) == fingerprint(*base)
    for i, other in enumerate(("h2", "m2", "Puck", "other-model", "altra nota", "f")):
        changed = list(base)
        changed[i] = other
        assert fingerprint(*changed) != fingerprint(*base), i


ROSTER = {"m1": {"gemini_voice": "Charon", "model": "mod", "notes": "nota"}}


def _fp(it, voice_id="m1", sex="m", values=()):
    r = ROSTER[voice_id]
    return fingerprint(text_hash(it, values), voice_id, r["gemini_voice"], r["model"], r["notes"], sex)


def test_in_step_reports_missing_and_stale_files():
    lines = {"1-description": "Nuovo testo.", "1-progress": "Altro."}
    jobs = [Job("1-description", "1-description", "m1", "m"), Job("1-progress", "1-progress", "m1", "m")]
    audio = {"1-description": {"fingerprint": _fp("Vecchio testo.")}}
    assert in_step(jobs, lines, ROSTER, audio) == {"missing": ["1-progress"], "stale": ["1-description"]}


def test_in_step_is_empty_when_the_files_match():
    lines = {"1-description": "Ben fatto, {name}!"}
    jobs = [Job("1-description", "1-description", "m1", "m"), Job("1-description_f", "1-description", "m1", "f")]
    audio = {"1-description": {"fingerprint": _fp(lines["1-description"])},
             "1-description_f": {"fingerprint": _fp(lines["1-description"], sex="f")}}
    assert in_step(jobs, lines, ROSTER, audio) == {"missing": [], "stale": []}
    audio["1-description_f"] = {"fingerprint": _fp(lines["1-description"], sex="m")}
    assert in_step(jobs, lines, ROSTER, audio)["stale"] == ["1-description_f"]


def test_in_step_reads_numbers_and_spoken_versions():
    lines = {"1-description": "Porta $N1 pelli, {class}."}
    jobs = [Job("1-description", "1-description", "m1", "m")]
    spoken = {"1-description": "Porta $N1 pelli, campione."}
    audio = {"1-description": {"fingerprint": fingerprint(
        text_hash(lines["1-description"], ("3",), spoken["1-description"]), "m1", "Charon", "mod", "nota", "m")}}
    assert in_step(jobs, lines, ROSTER, audio, {"1-description": ("3",)}, spoken) == {"missing": [], "stale": []}
    assert in_step(jobs, lines, ROSTER, audio, {"1-description": ("4",)}, spoken)["stale"] == ["1-description"]


def test_scopes_and_fields():
    assert voice.SCOPES["tirisfal"] == "pipeline/voice_tirisfal.txt"
    assert voice.FIELDS == ("description", "progress", "completion")
    assert voice.NARRATOR == "narrator" and voice.BOOK_NARRATOR == "book-narrator"


def test_scope_file_lists_quests_and_book_pages(tmp_path):
    f = tmp_path / "voice_tirisfal.txt"
    f.write_text("# Tirisfal\n364\n\n5 \nb 0123456789abcdef\n365  # un commento\n", encoding="utf-8")
    quests, books = read_scope_file(f)
    assert quests == (5, 364, 365)
    assert books == ("0123456789abcdef",)


@pytest.mark.parametrize("body", ["abc\n", "b XYZ\n", "12 34\n", "-3\n", "364\n364\n"])
def test_scope_file_refuses_a_bad_line(tmp_path, body):
    f = tmp_path / "voice_tirisfal.txt"
    f.write_text(body, encoding="utf-8")
    with pytest.raises(VoiceError, match="voice_tirisfal.txt"):
        read_scope_file(f)
