"""`translate_lint` fails an Italian draft row for each problem it names and passes only clean rows."""

from pathlib import Path

import pytest

from wfj.core import align
from wfj.dev import translate_lint as tl
from wfj.dev.translate_batch import read_jsonl, write_jsonl

ALLOW = {"horde"}


def _row(en, kind="completion", ref="r"):
    return {"ref": ref, "kind": kind, "en": en, "targets": [[1, "completion"]]}


def _check(en, it, kind="completion"):
    return tl.check_row(_row(en, kind), it, ALLOW)


def test_a_clean_row_passes():
    en = "Thank you, {name}. Take these 3 coins to Stormwind.\n\nThe Horde thanks you."
    it = "Grazie, {name}. Porta queste 3 monete a Roccavento.\n\nL'Orda ti ringrazia."
    assert _check(en, it) == []


@pytest.mark.parametrize(
    ("en", "it", "reason"),
    [
        ("Thank you.", "Thank you.", "not_italian"),
        ("Thank you.", "谢谢你们。", "not_italian"),
        ("Thank you, {name}.", "Grazie.", "tokens:{name}×1→none"),
        ("Hi {name}.", "Ciao {name}, {name}.", "tokens:{name}×1→{name}×2"),
        ("Hi {race}.", "Ciao {class}.", "tokens:{race}×1→{class}×1"),
        ("Thanks $Gsir:madam;.", "Grazie, $Gsignore:signora;.", "leftover:$G"),
        ("Thanks.", "Grazie, {foo}.", "leftover:{foo}"),
        ("One.\n\nTwo.", "Uno. Due.", "paragraphs:1/2"),
        ("We have $1997w of $1998w bars.", "Ne abbiamo 1997 su $1998w.", "counters:$1997w×1,$1998w×1→$1998w×1"),
        ("Bring me three.", "Portamene 4.", "numbers_changed:4"),
    ],
)
def test_each_reason(en, it, reason):
    assert reason in _check(en, it)


def test_italian_words_the_english_does_not_have_are_no_problem():
    """In Italian a Latin word the English lacked was a name gone wrong (`alignment_failed`); in Italian every
    word is Latin, so the lint has no such rule."""
    assert _check("Go north to Goldshire.", "Vai a nord, verso Borgodoro.") == []


def test_server_counters_kept_exactly_pass():
    assert _check("We have $1997w of $1998w bars.", "Abbiamo $1997w lingotti su $1998w.") == []


def test_an_upper_case_counter_is_a_counter():
    en = "Number of necropolises remaining: $2283W"
    assert _check(en, "Necropoli rimaste: $2283W") == []
    assert "counters:$2283W×1→none" in _check(en, "Necropoli rimaste: 2283")


def _files(tmp_path, batch, draft):
    b, d = tmp_path / "b.jsonl", tmp_path / "b.draft.jsonl"
    write_jsonl(b, batch)
    write_jsonl(d, draft)
    return b, d


def test_lint_coverage_and_ok_rows(tmp_path):
    batch = [_row("Hello.", ref="a"), _row("Bye.", ref="b"), _row("Hi.", ref="c"), _row("Yo.", ref="d")]
    draft = [
        {"ref": "a", "it": "Salve.  "},
        {"ref": "b", "it": "Arrivederci."},
        {"ref": "b", "it": "Addio."},  # duplicate
        {"ref": "z", "it": "Cosa."},  # unknown
        {"ref": "d", "it": "Yo."},  # fails a check
    ]  # c missing
    ok, failures = tl.lint(*_files(tmp_path, batch, draft), ALLOW)
    assert [r["ref"] for r in ok] == ["a"]
    assert ok[0] == {"ref": "a", "kind": "completion", "it": "Salve.", "targets": [[1, "completion"]]}
    assert failures == {"b": ["duplicate"], "z": ["unknown_ref"], "c": ["missing"], "d": ["not_italian"]}


def test_main_writes_ok_file_and_exit_code(tmp_path, capsys):
    b, d = _files(tmp_path, [_row("Hello.", ref="a")], [{"ref": "a", "it": "Salve."}])
    assert tl.main([str(b), str(d)]) == 0
    assert read_jsonl(tmp_path / "b.draft.ok.jsonl")[0]["it"] == "Salve."
    b, d = _files(tmp_path, [_row("Hello.", ref="a")], [{"ref": "a", "it": "Hello."}])
    assert tl.main([str(b), str(d)]) == 1
    assert "a: not_italian" in capsys.readouterr().out


def test_committed_allowlist_loads(root: Path):
    assert align.load_allowlist((root / tl.ALLOWLIST).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("en", "it", "ok"),
    [
        ("...", "...", True),
        ("...", "…", True),
        ("Hello...", "...", False),
        ("...", "Hello", True),  # a dots-only English may be written out in words too
    ],
)
def test_a_dots_only_line_may_stay_dots(en, it, ok):
    assert ("not_italian" not in _check(en, it, kind="gossip")) is ok


def test_a_short_book_row_gets_every_reason():
    assert "not_italian" in _book("Welcome!", "Welcome!")
    assert _book("Welcome!", "Benvenuto!") == []


# ── book pages ─────────────────────────────────────────────────────────────

HTML_EN = '<HTML>\n<BODY>\n<BR/>\n<H1 align="center">\nKurdran Wildhammer\n</H1>\n<P>\nHe rode the winds.\n</P>\n</BODY>\n</HTML>'
HTML_IT = '<HTML>\n<BODY>\n<BR/>\n<H1 align="center">\nKurdran Wildhammer\n</H1>\n<P>\nCavalcava i venti.\n</P>\n</BODY>\n</HTML>'


def _book(en, it, kind="book"):
    return tl.check_row({"ref": "r", "kind": kind, "en": en, "targets": [[1, "text"]]}, it, ALLOW)


def test_an_html_page_keeping_every_tag_passes_with_no_tag_reasons():
    assert _book(HTML_EN, HTML_IT) == []


@pytest.mark.parametrize(
    ("it", "reason"),
    [
        (HTML_IT.replace("<BR/>\n", ""), "markup_changed:tag 3: en <BR /> it <H1 align=\"center\">"),
        (HTML_IT.replace("<P>\nCavalcava i venti.\n</P>", "Cavalcava i venti."), "markup_changed:tag 6: en <P> it </BODY>"),
        (HTML_IT.replace("</BODY>", "<BR/>\n</BODY>"), "markup_changed:tag 8: en </BODY> it <BR />"),
        (HTML_IT.replace('<H1 align="center">', '<H1 align="left">'), "markup_changed:tag 4"),
    ],
)
def test_an_html_page_that_changes_its_tags_fails(it, reason):
    reasons = _book(HTML_EN, it)
    assert any(r.startswith(reason) for r in reasons), reasons


def test_markup_changed_never_applies_to_plain_text():
    # a plain page's bracketed prose is not markup (ADR-022)
    assert not any(r.startswith("markup_changed") for r in _book("A <illegible text> note.", "Un biglietto illeggibile."))
    assert not any(r.startswith("markup_changed") for r in _check("<P>Hi</P> there.", "Ciao a tutti."))


def test_a_space_only_line_is_one_break_on_both_sides():
    # book pages carry "\n \n"; the English and the Italian count it the same way
    # `lint` canonicalises the draft's breaks before checking it
    assert _book("One.\n \nTwo.", tl.paragraphs.normalize_breaks("Uno.\n \nDue.")) == []
    assert _book("One.\n \nTwo.", "Uno.\n\nDue.") == []
    assert "paragraphs:1/2" in _book("One.\n \nTwo.", "Uno. Due.")


# ── tooltips: `$N<k>` / `$D<k>` ───────────────────────────────────────────────

def _tooltip(en, kind="item_description"):
    return {"ref": "r1", "kind": kind, "en": en, "targets": [[117, "description"]]}


def _reasons(row, it):
    return tl.check_row(row, it, ALLOW)


SEATED = "Restores $o1 health over $d. Must remain seated while eating."


def test_the_value_placeholder_passes_but_a_baked_number_does_not():
    row = _tooltip(SEATED)
    assert _reasons(row, "Ripristina $N1 punti Salute in $D1. Devi restare seduto mentre mangi.") == []
    baked = _reasons(row, "Ripristina 61 punti Salute in 18 s. Devi restare seduto mentre mangi.")
    assert any(r.startswith("numbers_changed:") for r in baked), baked


def test_any_other_dollar_code_left_in_a_draft_still_fails():
    row = _tooltip("Restores $o1 health over $d.")
    assert "leftover:$o" in _reasons(row, "Ripristina $o1 punti Salute in $d secondi.")
    assert "leftover:$B" in _reasons(row, "Ripristina $N1 punti Salute in $D1.$B")


def test_a_placeholder_past_the_templates_slots_is_refused():
    """`Align.fill` is closed-ended: one unfillable `$N<k>` drops the whole line back to English."""
    row = _tooltip("Restores $s1 health.")
    assert _reasons(row, "Ripristina $N1 punti Salute.") == []
    assert "value_index:2>1" in _reasons(row, "Ripristina $N1 punti Salute in $N2 s.")
    assert "value_index:3,4>1" in _reasons(row, "Ripristina $N1, $N3 e $N4 punti Salute.")


def test_the_index_is_not_checked_when_the_template_makes_it_unknowable():
    row = _tooltip("Absorbs $s1$?a1[ and $s2 more][]. Lasts $d.", kind="spell_description")
    assert not [r for r in _reasons(row, "Assorbe $N9 danni per $N5.") if r.startswith("value_index")]
    # arithmetic IS counted, so an index past it is caught
    sums = _tooltip("Deals ${$m1*2} damage over $d.", kind="spell_description")
    assert "value_index:9>2" in _reasons(sums, "Infligge $N9 danni in $D1.")


def test_a_literal_the_template_shows_may_be_written_as_a_literal():
    row = _tooltip("Teaches Frost Ward (Rank 5).")
    assert _reasons(row, "Insegna Frost Ward (Grado 5).") == []
    wrong = _reasons(row, "Insegna Frost Ward (Grado 6).")
    assert any(r.startswith("numbers_changed:") for r in wrong), wrong


def test_a_duration_must_be_carried_as_a_placeholder_not_a_named_unit():
    """The unit is the client's choice, and `Align.check` cannot catch a wrong one; this is the only gate."""
    row = _tooltip(SEATED)
    named = _reasons(row, "Ripristina $N1 punti Salute in $N2 s. Devi restare seduto mentre mangi.")
    assert "duration_missing:D1" in named
    baked = _reasons(row, "Ripristina 61 punti Salute in 18 s. Devi restare seduto mentre mangi.")
    assert "duration_missing:D1" in baked
    assert any(r.startswith("numbers_changed:") for r in baked)


def test_every_duration_of_a_template_needs_its_own_placeholder():
    row = _tooltip("Stuns for $d and slows for $d1.", kind="spell_description")
    assert _reasons(row, "Stordisce per $D1 e rallenta per $D2.") == []
    assert "duration_missing:D2" in _reasons(row, "Stordisce per $D1 e rallenta.")
    assert "duration_index:3>2" in _reasons(row, "Stordisce per $D1 e rallenta per $D3.")


def test_a_template_with_no_duration_needs_no_placeholder():
    row = _tooltip("Restores $s1 health.")
    assert not [r for r in _reasons(row, "Ripristina $N1 punti Salute.") if r.startswith("duration")]


def test_the_duration_rule_is_skipped_when_the_template_is_uncountable():
    row = _tooltip("Absorbs $s1$?a1[ more][]. Lasts $d.", kind="spell_description")
    assert not [r for r in _reasons(row, "Assorbe $N1 danni.") if r.startswith("duration")]
    sums = _tooltip("Deals ${$m1*2} damage over $d.", kind="spell_description")
    assert "duration_missing:D1" in _reasons(sums, "Infligge $N1 danni.")


def test_a_client_templates_arithmetic_is_not_a_player_token():
    """`${$m1/60}` is Blizzard arithmetic: a value the client computes, carried by `$N<k>`, never copied."""
    row = _tooltip("Coats a weapon with poison that lasts for ${$m1/60} minutes.", kind="spell_description")
    assert _reasons(row, "Ricopre un'arma con un veleno che dura $N1 minuti.") == []
    two = _tooltip("Causes ${$m2*$<dmg>} to ${$M2*$<dmg>} Frost damage.", kind="spell_description")
    # a range is one value the addon fills as `14-22`, so `$N1-$N2` points past it
    assert _reasons(two, "Infligge $N1 danni da Gelo.") == []
    assert "value_index:2>1" in _reasons(two, "Infligge $N1-$N2 danni da Gelo.")
    assert any(r.startswith("leftover:") for r in _reasons(row, "Ricopre un'arma con un veleno che dura ${$m1/60} minuti."))
    named = _tooltip("Greetings {name}, this deals $s1 damage.", kind="spell_description")
    assert any(r.startswith("tokens:") for r in _reasons(named, "Infligge $N1 danni."))
    assert _reasons(named, "Salve {name}, infligge $N1 danni.") == []


def test_the_home_location_code_is_not_a_value_slot():
    """`$z` prints the player's home town, not a number."""
    en = "Returns you to $z. Speak to an Innkeeper in a different place to change your home location."
    assert align.value_slots(en) == 0
    assert align.duration_slots(en) == 0
    row = _tooltip(en)
    assert _reasons(row, "Ti riporta a casa. Parla con un locandiere altrove per cambiarla.") == []
    assert "value_index:1>0" in _reasons(row, "Ti riporta a $N1. Parla con un locandiere altrove per cambiarla.")


def test_a_placeholder_with_english_glued_to_it_is_refused():
    row = _tooltip("Permanently enchant a head slot item to increase Attack Power by $s1.",
                   kind="spell_description")
    assert "placeholder_run:$N1c1" in _reasons(row, "Aumenta il Potere d'attacco di $N1c1.")
    assert _reasons(row, "Aumenta il Potere d'attacco di $N1.") == []
    proc = _tooltip("Restores $s1 mana. This effect cannot occur more than once every $proccooldown sec.",
                    kind="spell_description")
    assert "placeholder_run:$N2roccooldown" in _reasons(proc, "Ripristina $N1 Mana. Al massimo una volta ogni $N2roccooldown s.")
    assert _reasons(proc, "Ripristina $N1 Mana. Al massimo una volta ogni $N2 s.") == []


def test_the_precision_digit_cannot_vouch_for_a_number_in_the_italian():
    row = _tooltip("Improves your chance to get a critical strike with spells by ${$s1}.1%.",
                   kind="spell_description")
    assert _reasons(row, "Aumenta la probabilità di critico degli incantesimi del $N1%.") == []
    assert "numbers_changed:1" in _reasons(row, "Aumenta la probabilità di critico degli incantesimi del $N1.1%.")
    assert "value_index:2>1" in _reasons(row, "Aumenta la probabilità di critico degli incantesimi del $N1.$N2%.")


def test_newlines_inside_arithmetic_are_not_paragraphs():
    row = _tooltip("Absorbs ${$m1+\n$m2+\n$m3} damage.", kind="spell_description")
    assert _reasons(row, "Assorbe $N1 danni.") == []


def test_a_tooltips_cross_spell_code_is_not_a_quest_counter():
    row = _tooltip("Suffering $1310167w2 damage every $t1 sec.", kind="spell_aura")
    assert not [r for r in _reasons(row, "Subisce $N1 danni ogni $N2 s.") if r.startswith("counters")]
    quest = {"ref": "r", "kind": "completion", "en": "You have $1997w left.", "targets": [[1, "completion"]]}
    assert any(r.startswith("counters") for r in _reasons(quest, "Ne mancano pochi."))


def test_a_value_the_client_fills_in_cannot_be_dropped():
    writ = {"ref": "r", "kind": "quest_description",
            "en": "The note is requesting $2oa Elixir of Ogre's Strength.", "targets": [[1, "description"]]}
    assert "slot_missing:N1" in _reasons(writ, "Il biglietto richiede Elisir di Forza dell'Ogre.")
    assert _reasons(writ, "Il biglietto richiede $N1 Elisir di Forza dell'Ogre.") == []


def test_a_literal_the_english_shows_may_be_written_out_instead():
    row = {"ref": "r", "kind": "quest_objectives", "en": "Kill 7 Young Nightsabers.",
           "targets": [[1, "objectives"]]}
    assert _reasons(row, "Uccidi 7 Giovani Fiersciabola.") == []
    assert _reasons(row, "Uccidi $N1 Giovani Fiersciabola.") == []


def test_values_and_durations_are_counted_in_their_own_namespaces():
    row = _tooltip("Increases resistance to Shadow spells by $s1 for $d.", kind="spell_description")
    assert _reasons(row, "Aumenta la resistenza agli incantesimi d'Ombra di $N1 per $D1.") == []
    assert "duration_missing:D1" in _reasons(row, "Aumenta la resistenza agli incantesimi d'Ombra di $N1.")


def test_a_name_list_tail_is_one_trailing_marker():
    en = "You are fluent in the following languages:$?s668[\r\n$@spellname668][]$?s669[\r\n$@spellname669][]"
    assert _check(en, "Parli fluentemente le seguenti lingue:$T", kind="spell_description") == []
    assert "tail_missing" in _check(en, "Parli fluentemente le seguenti lingue:", kind="spell_description")
    assert "tail_misplaced" in _check(en, "$TParli fluentemente le seguenti lingue:", kind="spell_description")
    assert "tail_unexpected" in _check("Deals $s1 damage.", "Infligge $N1 danni.$T", kind="spell_description")


RIDING = ("Allows you to ride basic ground mounts that require a riding skill of 75.\r\n\r\nKnown abilities:"
          "$?s824[\r\n$@spellname824][]$?s18995[\r\n$@spellname18995][]")


def test_a_tail_after_a_multi_line_head_keeps_the_heads_breaks():
    row = {**_row(RIDING, "spell_description"), "tail": True, "slots": 1}
    good = "Permette di cavalcare cavalcature terrestri base che richiedono Equitazione $N1.\n\nAbilità conosciute:$T"
    assert _reasons(row, good) == []
    assert "tail_breaks" in _reasons(row, good.replace("\n\n", " "))


def test_an_npc_emote_keeps_the_speakers_name_slot():
    row = {"ref": "r", "kind": "gossip", "en": "%s goes into a frenzy!", "targets": [["r", "text"]]}
    assert not [r for r in _reasons(row, "%s va su tutte le furie!") if r.startswith("speaker")]
    assert "speaker:1→0" in _reasons(row, "Va su tutte le furie!")
    assert "speaker:1→1" in _reasons(row, "%s va al 100% su tutte le furie!")


def test_only_a_name_only_tooltip_row_may_keep_its_english():
    name = {**_tooltip("Umbrinoth"), "title_case": True, "names": ["Umbrinoth"], "name_only": True}
    assert _reasons(name, "Umbrinoth") == []
    flavour = {**_tooltip("Made With Love"), "title_case": True}
    assert _reasons(flavour, "Made With Love") == ["not_italian"]


def test_a_draft_rows_words_are_not_carried(tmp_path):
    b, d = _files(tmp_path, [_row("Guard the forest.", ref="a")],
                  [{"ref": "a", "it": "Proteggi la foresta.", "words": [["foresta", "x"]]}])
    ok, failures = tl.lint(b, d, ALLOW)
    assert failures == {} and "words" not in ok[0]


# ── branch variants and included icons (ADR-043) ─────────────────────────────

FIRE_WARD = "Absorbs $s1 Fire damage$?s11094[ and grants a $s2% chance to reflect Fire spells][]. Lasts $d."


def _branch_row(en):
    return {**_row(en, "spell_description"), "branches": 2}


def test_a_branch_row_is_checked_variant_by_variant():
    ok = "Assorbe $N1 danni da Fuoco$?s11094[ e dà il $N2% di probabilità di riflettere gli incantesimi di Fuoco][]. Dura $D1."
    assert tl.check_row(_branch_row(FIRE_WARD), ok, ALLOW) == []
    no_clause = "Assorbe $N1 danni da Fuoco. Dura $D1."
    assert tl.check_row(_branch_row(FIRE_WARD), no_clause, ALLOW) == ["branch_skeleton"]
    dropped = "Assorbe $N1 danni da Fuoco$?s11094[ e riflette gli incantesimi di Fuoco][]. Dura $D1."
    assert tl.check_row(_branch_row(FIRE_WARD), dropped, ALLOW) == ["v1:slot_missing:N2"]


def test_branches_named_apart_pass():
    en = "Add the sign to your $?pc923[Orcish Tradeskill Sign][Dwarven Tradeskill Sign] toy."
    named = "Aggiungi al tuo giocattolo $?pc923[Orcish Tradeskill Sign][Dwarven Tradeskill Sign]."
    assert tl.check_row(_branch_row(en), named, ALLOW) == []


@pytest.mark.parametrize(("it", "reason"), [
    ("Infligge $N1 danni. Quick Draw.", "icon_missing:1"),
    ("$I1 $I1 Infligge $N1 danni. Quick Draw.", "icon_index:1"),
    ("$I2 Infligge $N1 danni. Quick Draw.", "icon_index:2"),
])
def test_icons_are_carried_once_each(it, reason):
    reasons = tl.check_row(_row("Gain $I1 Quick Draw: $s1 damage.", "spell_description"), it, ALLOW)
    assert reason in reasons


def test_an_icon_placeholder_is_not_a_leftover_code():
    it = "Ottieni $I1 Quick Draw: $N1 danni."
    assert tl.check_row(_row("Gain $I1 Quick Draw: $s1 damage.", "spell_description"), it, ALLOW) == []


def test_a_keyed_branch_row_passes_when_its_wordings_differ():
    en = ("$?s436895[Increases all damage you deal by $s1%.]"
          "[Increases the damage you deal with physical attacks in all forms by $s1%.]")
    it = ("$?s436895[Aumenta tutti i danni inflitti del $N1%.]"
          "[Aumenta i danni degli attacchi fisici in tutte le forme del $N2%.]")
    assert tl.check_row(_branch_row(en), it, ALLOW) == []
