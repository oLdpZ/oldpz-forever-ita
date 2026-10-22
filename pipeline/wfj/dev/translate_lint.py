"""Check a drafted translation batch before it is expanded and imported.

    python -m wfj.dev.translate_lint BATCH DRAFT [--allowlist PATH]

Every batch row must have exactly one draft row, and every draft row a batch row. A draft fails with one
reason per problem:

- `missing` / `duplicate` / `unknown_ref`: the draft does not cover the batch one to one
- `not_italian`: no Latin letter, or the English unchanged (`language.is_italian`). An English line that is
  only dots (`...`) may stay only dots (`…`), and a tooltip row `cut` marked `name_only` (`Umbrinoth`) may
  keep exactly its English.
- `tokens:<english>→<italian>`: the `{name}` / `{class}` / `{race}` tokens differ in kind or count
- `placeholder_lost:<token>`: a player token of the English (`{name}`, `{class}`, `{race}`: `$N` / `$C` /
  `$R` as `model_english` shows them) that the Italian does not carry at all. The player would read a
  sentence missing their name, or one with a name the drafter made up. A gender choice of the English
  (`$Gsir:madam;`, `<sir/madam>`) may become an Italian pair (`<signore/signora>`) or a neutral wording:
  never lost.
- `glossary_term:<en>→<it>`: the English holds a `zona`, `fazione`, `classe` or `razza` name of the official
  glossary (the row's `glossary`, attached by `translate_batch cut`) and the Italian carries none of its
  Italian forms. The player reads the official Italian name everywhere else in the game. A name word inside
  a longer capitalized proper name (`Mage Quarter`: "Quartiere dei Maghi"; a creature `Redridge Mongrel`)
  only warns.
- `leftover:<token>`: a `$` code, an unknown `{word}` or a `<x/y>` pair the addon cannot expand (a gender pair
  of words, `<il/la>`, is expanded by the player's sex)
- `counters:<english>→<italian>`: the server counters (`$1997w`, `$2283W`: a value the game fills in) differ
- `paragraphs:<it>/<en>`: a different number of paragraphs
- `numbers_changed:<n>`: a number in the Italian that the English does not have (`align.check_numbers`).
  This is what stops a tooltip draft baking a literal value: the English template holds `$s1`, not `58`,
  so a Italian line saying `58` fails. Write `$N<k>` instead. The addon fills it from the k-th number
  of the line the client is showing, so the translation survives a different rank, level or talent.
- `placeholder_run:<text>`: a `$N<k>` or `$D<k>` with letters glued to its end (`$N1c1`,
  `$N2roccooldown`). The placeholder fills and the glued fragment stays on screen, and no other rule can
  see it, because a fragment of the English source is by definition present in the English.
- `slot_missing:N<k>`: the k-th number of the line comes from a code the client fills in (`$s1`, `$1oa`,
  `${…}`) and the Italian has no `$N<k>` for it (nor, where the line shows it as a duration, its `$D<j>`).
  Dropping one takes the number off the screen, and a placeholder pointing at another slot does not
  carry it. A literal the English already shows (`Kill 7 Nightsabers`) is exempt: write it out or use
  `$N<k>`.
- `duration_as_value:N<k>`: `$N<k>` on a `$d`, the bare number, with a unit the Italian named itself.
- `duration_missing:D<j>`: the j-th duration is a `$d` and the Italian has no `$D<j>`. A duration is the
  one value whose **unit** the client chooses, so a Italian line that names the unit itself (`18 sec`) is
  wrong the moment the client renders minutes. `Align.check` cannot catch it, because the number
  matches and the unit is Italian text the gate never reads. `$D<k>` copies the whole phrase out of the
  live line, rendered by the UI strings we already ship (`INT_SPELL_DURATION_SEC`, …). Durations
  are counted the way the addon reads the live line: a number the English writes in front of a unit
  (`every 5 sec`) is a duration too, so `$D` indices count it.
- `duration_index:<k>><n>`: a `$D<k>` past the durations the template prints. `$D` indexes the line's
  durations (`$D1` is the first), not the whole number space `$N` indexes.
- `value_index:<k>><slots>`: a `$N<k>` past the number of values the template can print. The addon's
  fill is closed-ended: one unfillable placeholder drops the whole line back to English. Not reported
  when the template's slot count is unknowable (`$?…[…]` conditionals,
  `$@spelldesc…` inclusions); there the count is checked in game, not here.
- `icon_missing:<k>` / `icon_index:<k>`: every `$I<k>` of the English (an inline spell icon,
  `$@spellicon`) once in the Italian, and no other. The addon copies the k-th icon of the live line there.
- Branch rows (ADR-043; the row carries `branches`): `branch_skeleton`, the Italian does not keep
  the English's `$?` conditionals (same conditions, branch counts and order); `branch_index:<N|D><k>`, a
  placeholder for a value the variant it sits in does not print (whole-template numbering, `row["slots"]`);
  `v<i>:<reason>`, variant i fails an ordinary rule against its own English; `branches_indistinguishable`,
  on every variant's line another variant's Italian would pass the addon's gate too, so the addon (which
  shows a variant only when exactly one fits) would never show any; `branches_unsafe`, a shadowed variant
  carries an icon or a duration the variant shadowing it lacks, so a fill failure would show the wrong branch.
- Warning (the row still passes): `glossary_term:<en>→<it>`, the same for an `oggetto` or `abilita` term, a
  `curato` name (`pipeline/glossario_curato.tsv`: the coordinator's, not Blizzard's) (or
  a glossary pair without a kind): the client's tracker and tooltips may still show that name in English
- `markup_changed:<difference>`: an HTML book page (`<HTML…`) whose Italian does not carry the English's
  tags in the same order (`markup.html_mismatch`, the rule `wfj check` applies to book pages)

A draft row `{"ref": …, "it": null}` says the line correctly stays English (a quest title that is only a
proper name): it is `kept_english`, neither translated nor failed, and counts as present for `missing` /
`duplicate`. Kept rows go to `<DRAFT stem>.keep.jsonl` (`translate_batch keep` records them in
`pipeline/keep_english.tsv`, so `cut` does not select them again while the English is unchanged); they are
never imported.

Passing rows, with paragraph breaks canonicalised, go to `<DRAFT stem>.ok.jsonl` with the batch's `kind` and
`targets`. Exit 1 when any row failed.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from wfj.core import align, language, markup, paragraphs, placeholders
from wfj.core.names import strip_marks
from wfj.dev.translate_batch import read_jsonl, write_jsonl

ALLOWLIST = Path("pipeline/allowlist.txt")
_DOTS = re.compile(r"[.…\s]+")
# A quest's server counter (`$1997w`). The trailing boundary matters: a tooltip's cross-spell value code
# `$1310167w2` starts the same way and is NOT a counter to copy through.
_COUNTER = re.compile(r"\$\d+[wW](?![0-9])")
_RUN_ON = re.compile(r"\$[NDI]\d+[A-Za-z][A-Za-z0-9]*")  # a placeholder with English glued to its end
# `$N<k>` and `$D<k>` are the addon's placeholders, not leftover codes: the value and the duration of the
# line the client is showing. Every other `$` in a draft is a leftover, except a line's last `$T`, the
# name-list tail, whose placement `align.tail_problems` judges.
_CODE = re.compile(r"\$(?!\d+[wW]|[NDI]\d|T\Z)\S?")


# A client template's arithmetic is `${$m1/60}`: a `$` then a braced expression. Its inner braces
# are not a player token, and a draft must NOT copy it through (`$` codes are `leftover`), so it is stripped
# before the token sets are compared. The server-only kinds never carry one; the tooltip kinds do.
_SUM = re.compile(r"\$\{[^{}]*\}")
PLAYER_TOKENS = tuple(f"{{{w}}}" for w in placeholders.KNOWN)  # {name} {class} {race}
# the glossary kinds a draft must write the official Italian of; the others only warn
NAME_KINDS = frozenset({"zona", "fazione", "classe", "razza"})


# a clock time of the English glued to `am` / `pm`: `6PM`, `2pm`, `6:30 PM`
_CLOCK = re.compile(r"(?<![A-Za-z0-9])(\d{1,2})(:\d\d)?\s*([ap])m\b", re.I)


def _clock_numbers(en: str) -> str:
    """The English with each `6PM` also written as its 24-hour value (` 6 18 `): the Italian may say `alle 6
    di sera` or `alle 18`. `align.numbers` does not read a number glued to letters."""
    def read(m: re.Match[str]) -> str:
        hour, minutes, pm = int(m.group(1)), (m.group(2) or "").replace(":", " "), m.group(3).lower() == "p"
        return f" {hour}{minutes} {hour % 12 + (12 if pm else 0)}{minutes} "
    return _CLOCK.sub(read, en)


def _brace_tokens(text: str) -> Counter[str]:
    return Counter(t for t in placeholders.tokens(_SUM.sub("", text or "")) if t.startswith("{"))


def _value_index_problems(en: str, it: str) -> list[str]:
    """A `$N<k>` past the template's slots fills with nothing and the line is dropped in game
    (`Align.fill` fails closed). Only checked where the slot count is knowable from the template."""
    slots = align.value_slots(en)
    used = align.fill_indices(it)
    if slots is not None and used:
        over = sorted({k for k in used if k < 1 or k > slots})
        if over:
            return [f"value_index:{','.join(map(str, over))}>{slots}"]
    return []


def _duration_index_problems(en: str, it: str) -> list[str]:
    """A `$D<k>` past the template's durations, which the client cannot fill."""
    durations = align.duration_slots(en)
    if durations is not None:
        over = sorted({k for k in align.duration_indices(it) if k < 1 or k > durations})
        if over:
            return [f"duration_index:{','.join(map(str, over))}>{durations}"]
    return []


def check_row(row: dict[str, Any], it: str, allowlist: set[str]) -> list[str]:
    # a marked name (spec §8) is checked as the Italian the player reads by default; a draft carries none
    # (the pipeline marks at import), Blizzard's converted text neither (marked after this check)
    it = strip_marks(it)
    if row.get("branches"):
        return _check_branches(row, it, allowlist)
    en = row["en"]
    reasons: list[str] = []
    # a tooltip line that is only a name (`translate_batch` marks it `name_only`) ships that name: names stay
    # in English letters
    kept_name = bool(row.get("name_only")) and it == en
    dots = bool(_DOTS.fullmatch(en) and _DOTS.fullmatch(it))
    if not language.is_italian(it, en) and not dots and not kept_name:
        return ["not_italian"]
    want, have = _brace_tokens(en), _brace_tokens(it)
    if want != have:
        reasons.append(f"tokens:{_fmt(want)}→{_fmt(have)}")
    reasons += [f"placeholder_lost:{t}" for t in want if t in PLAYER_TOKENS and t not in have]
    # a gender pair (`<il/la>`, `<caro/cara>`) is Italian the addon expands by the player's sex: no leftover
    leftovers = placeholders.unknown(it)
    leftovers += _CODE.findall(it)
    if Counter(_COUNTER.findall(en)) != Counter(_COUNTER.findall(it)):
        reasons.append(f"counters:{_fmt(Counter(_COUNTER.findall(en)))}→{_fmt(Counter(_COUNTER.findall(it)))}")
    reasons += [f"leftover:{t}" for t in dict.fromkeys(leftovers)]
    # NPC speech: an emote's `%s` is the speaker's name the client fills in (the chat line is
    # formatted with it, chatframeoverrides.lua:640–644): the Italian keeps every `%s` and carries no other
    # `%`, which the client's format() would read as a specifier
    if en.count("%s") != it.count("%s") or it.replace("%s", "").count("%") > en.replace("%s", "").count("%"):
        reasons.append(f"speaker:{en.count('%s')}→{it.count('%s')}")
    # A placeholder must end where its digits end. `$N1c1`, `$N2roccooldown` (a drafter gluing a
    # fragment of the English source onto one) fills the value and leaves the fragment on screen, and the
    # name check vouches for the fragment because it IS a substring of the English.
    reasons += [f"placeholder_run:{t}" for t in dict.fromkeys(_RUN_ON.findall(it))]
    reasons += _value_index_problems(en, it)
    # A duration's UNIT is the client's choice: `$d` renders through INT_SPELL_DURATION_SEC /
    # _MIN / _HOURS / _DAYS, so one template is seconds on one item and minutes on another.
    # `Align.check` cannot catch a wrong unit (the number matches and the unit is Italian text the gate
    # never reads), so this is the only gate: one `$D<k>` per duration, never a unit named by hand.
    # A value the client fills in cannot be stated by the Italian, so dropping it loses the number off the
    # screen. A literal the English already shows is exempt: the Italian may write it out instead.
    # Every code slot must be carried by the placeholder that points at IT. A mere count of placeholders
    # would pass `Ripristina $N2 punti Salute in $D1` for `Restores $o1 health over $d`, dropping `$o1` and
    # showing the duration's number as the health. A `$d` takes only its `$D<k>` (ADR-028: the client picks
    # the unit).
    reasons += align.slot_problems(en, it) or []
    # a name-list tail (Languages, Armor Proficiency) is carried by one trailing `$T`, never written out
    reasons += align.tail_problems(en, it)
    reasons += _duration_index_problems(en, it)
    reasons += _icon_problems(en, it)
    # both sides counted the same way: a line holding only spaces between two breaks is one break.
    # A `${…}` sum may hold newlines (`${$m1+\n$m2}`), which are inside a code the client
    # computes, never paragraph breaks the Italian has to mirror.
    # a name-list tail is copied from the live line, so the Italian mirrors the head's paragraphs only
    jp = paragraphs.count(it)
    ep = paragraphs.count(paragraphs.normalize_breaks(align.SUM.sub(" ", align.split_tail(en)[0])))
    if jp != ep:
        reasons.append(f"paragraphs:{jp}/{ep}")
    # The `.N` of `${…}.N` is Blizzard's precision, not a number the player reads: the line
    # prints `2.5%`, never a `1`. Left in, it would vouch for a Italian `$N1.1%`, which fills one value
    # and then states a decimal of its own.
    numbers_en = _clock_numbers(align.SUM.sub(" ", en))
    reasons += [f"numbers_changed:{n}" for n in align.check_numbers(it, numbers_en)[1]]
    if bad_html := markup.html_mismatch(en, it):  # an HTML book page keeps its tags in order
        reasons.append(f"markup_changed:{bad_html}")
    return reasons


def _icon_problems(en: str, it: str) -> list[str]:
    """Every `$I<k>` of the English once in the Italian: `icon_missing:<k>` (an icon the line
    would lose), `icon_index:<k>` (one the English does not have, or written twice)."""
    want, have = Counter(align.icon_indices(en)), Counter(align.icon_indices(it))
    out = [f"icon_missing:{k}" for k in sorted(want) if k not in have]
    out += [f"icon_index:{k}" for k in sorted(have) if have[k] > want.get(k, 0)]
    return out


def _check_branches(row: dict[str, Any], it: str, allowlist: set[str]) -> list[str]:
    """A `$?` row (ADR-043). The Italian keeps the English's conditionals (`branch_skeleton`); each
    variant, renumbered to its own reading order (`align.it_variants`), is checked against that variant's
    English by every rule of an ordinary row (a reason is prefixed `v<i>:`); and the addon must be able to
    show at least one variant, refused when on every variant's line another variant passes the gate too
    (`branches_indistinguishable`, `align.unshowable`: wordings told apart by a key ship)."""
    b = align.branching(row["en"])
    if b.reason:
        return [b.reason]
    texts, bad = align.it_variants(it, b)
    if texts is None:
        return bad
    reasons: list[str] = []
    for i, (v, text) in enumerate(zip(b.variants, texts, strict=True), 1):
        sub = {**row, "en": v.en}
        sub.pop("branches", None)
        reasons += [f"v{i}:{r}" for r in check_row(sub, text, allowlist)]
    if b.sectioned:  # its paragraphs are told apart by their opening words (align.section_prefix)
        return reasons
    shapes = [v.shape for v in b.variants]
    pairs = align.indistinguishable(texts, [v.en for v in b.variants], shapes, allowlist)
    if not reasons and align.unshowable(pairs, b.variants):
        reasons.append("branches_indistinguishable")
    elif not reasons and not align.never_shown(pairs, len(texts)) and align.unsafe_shadow(pairs, texts):
        reasons.append("branches_unsafe")  # a keyed line's variants are picked by key, so no shadow matters
    return reasons


# a name word that is only one word of a longer capitalized proper name ("Mage Quarter", official
# "Quartiere dei Maghi"; a creature "Redridge Mongrel") may rightly lose its own Italian form: kept as a
# warning, not an error
_NEXT_CAP = re.compile(r"(?:['’]s)?[ \t]+[A-Z]")
# a capitalized word right before the occurrence, with some text before it that does not end a sentence
_PREV_CAP = re.compile(r"(?P<before>.*\S)[ \t]+[A-Z][\w'’-]*[ \t]+\Z", re.S)
_SENTENCE_END = re.compile(r"[.!?:;\n][\W]*\Z")


def _embedded(en: str, term: str) -> bool:
    """Every occurrence of `term` in the English sits right after a capitalized word that does not start a
    sentence, or right before a capitalized word (past a possessive `'s`): part of a longer proper name.
    False when the English never shows the term."""
    hits = list(re.finditer(rf"(?<![\w]){re.escape(term)}(?![\w])", en, re.I))
    for m in hits:
        if _NEXT_CAP.match(en, m.end()):
            continue
        prev = _PREV_CAP.match(en[: m.start()])
        if prev and not _SENTENCE_END.search(prev.group("before")):
            continue
        return False
    return bool(hits)


# words inside a glossary term that are never inflected (`Elfo della Notte`: "elfi della notte")
_NO_INFLECT = frozenset({"di", "del", "dello", "della", "dei", "degli", "delle", "da", "dal", "dallo",
                         "dalla", "dai", "dagli", "dalle", "in", "nel", "nello", "nella", "nei", "negli",
                         "nelle",
                         "al", "allo", "alla", "ai", "agli", "alle", "il", "lo", "la", "i", "gli", "le", "un",
                         "uno", "una", "ed", "con", "su", "per", "tra", "fra"})
_PLURAL_ENDINGS = (("co", ("chi", "ci")), ("go", ("ghi", "gi")), ("ca", ("che",)), ("ga", ("ghe",)),
                   ("io", ("i",)), ("o", ("i",)), ("a", ("e",)), ("e", ("i",)))


def _plurals(word: str) -> list[str]:
    """The regular Italian plurals of a casefolded word (none when it does not end in a vowel or is a
    preposition or an article)."""
    if word in _NO_INFLECT:
        return []
    for end, plurals in _PLURAL_ENDINGS:
        if word.endswith(end) and len(word) > len(end):
            return [word[: -len(end)] + p for p in plurals]
    return []


def _inflections(form: str) -> set[str]:
    """The plural readings of `form`, casefolded, without the form itself: every mix of words inflected or
    left alone (`Elfo della Notte`: "elfi della notte", "elfi della notti")."""
    words = form.casefold().split()
    combos = [""]
    for w in words:
        combos = [f"{c} {o}".strip() for c in combos for o in [w, *_plurals(w)]]
    return set(combos) - {" ".join(words)}


def _carries(text: str, form: str, plurals: bool) -> bool:
    """The casefolded `text` holds `form` (as a substring, as ever) or, when `plurals`, one of its plural
    readings as whole words: `magi` must not be found in `magia`."""
    if form.casefold() in text:
        return True
    return plurals and any(re.search(rf"(?<!\w){re.escape(v)}(?!\w)", text) for v in _inflections(form))


def _glossary_missing(row: dict[str, Any], it: str, names: bool) -> list[str]:
    """`glossary_term:<en>→<it>` for each glossary term of the row whose Italian form (either one, for a class
    or race word) the draft does not carry, case-insensitively: the name kinds' terms (`names`) or the
    others. A term is a name when any of its entries has a name kind; an entry without a kind is not. A
    name term whose every English occurrence is inside a longer capitalized proper name (`_embedded`:
    "Mage Quarter", a creature "Redridge Mongrel") counts with the others: a warning."""
    forms: dict[str, list[str]] = {}
    kinds: dict[str, set[str]] = {}
    for en, form, *kind in row.get("glossary") or []:
        forms.setdefault(en, []).append(form)
        kinds.setdefault(en, set()).update(k for k in kind[:1] if k in NAME_KINDS)
    english = strip_marks(str(row.get("en") or ""))

    def strict(en: str) -> bool:
        ks = kinds[en]
        return bool(ks) and not _embedded(english, en)

    text = strip_marks(it or "").casefold()
    missing = [(en, fs) for en, fs in forms.items()
               if strict(en) == names and not any(_carries(text, f, not _embedded(english, en)) for f in fs)]
    # a name word inside a longer proper name keeps today's exact reading ("Quartiere dei Maghi" warns)
    return [f"glossary_term:{en}→{'/'.join(fs)}" for en, fs in missing]


def glossary_errors(row: dict[str, Any], it: str) -> list[str]:
    """The glossary terms of a name kind (`NAME_KINDS`) the draft does not carry: the row fails."""
    return _glossary_missing(row, it, names=True)


def glossary_warnings(row: dict[str, Any], it: str) -> list[str]:
    """The item / spell glossary terms, and the name words inside a longer proper name, the draft does not
    carry: the row still passes."""
    return _glossary_missing(row, it, names=False)


def warnings(batch: Path, draft: Path) -> dict[str, list[str]]:
    """The glossary warnings of every drafted row of the batch, by ref."""
    rows = {r["ref"]: r for r in read_jsonl(batch)}
    out: dict[str, list[str]] = {}
    for d in read_jsonl(draft):
        row = rows.get(d.get("ref"))
        if row is not None and not _kept(d) and (w := glossary_warnings(row, str(d.get("it") or ""))):
            out[d["ref"]] = w
    return out


def _fmt(c: Counter[str]) -> str:
    return ",".join(f"{t}×{n}" for t, n in sorted(c.items())) or "none"


def _kept(d: dict[str, Any]) -> bool:
    """`{"ref": …, "it": null}`: the drafter says the line correctly stays English (a title that is only a
    name). A row without `it` at all is not a decision, it is a draft that forgot the line."""
    return "it" in d and d["it"] is None


def lint_rows(
    batch: Path, draft: Path, allowlist: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[str]]]:
    """→ (ok rows, kept-English rows, failures by ref). A kept row counts as present for `missing` and
    `duplicate`, is checked by no rule of the Italian (there is none) and is never a translation."""
    rows = {r["ref"]: r for r in read_jsonl(batch)}
    failures: dict[str, list[str]] = {}
    seen: dict[str, str | None] = {}
    for d in read_jsonl(draft):
        ref = d.get("ref")
        if ref not in rows:
            failures.setdefault(str(ref), []).append("unknown_ref")
        elif ref in seen:
            failures.setdefault(ref, []).append("duplicate")
        else:
            seen[ref] = None if _kept(d) else paragraphs.normalize_breaks(str(d.get("it") or ""))
    ok: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for ref, row in rows.items():
        if ref not in seen:
            failures.setdefault(ref, []).append("missing")
            continue
        it = seen[ref]
        if it is None:
            if ref not in failures:
                kept.append({"ref": ref, "kind": row["kind"], "en": row["en"], "targets": row["targets"]})
            continue
        reasons = check_row(row, it, allowlist) + glossary_errors(row, it)
        if reasons or ref in failures:
            failures.setdefault(ref, []).extend(reasons)
        else:
            ok.append({"ref": ref, "kind": row["kind"], "it": it, "targets": row["targets"]})
    return ok, kept, failures


def lint(batch: Path, draft: Path, allowlist: set[str]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    ok, _, failures = lint_rows(batch, draft, allowlist)
    return ok, failures


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="translate_lint", description=__doc__.split("\n\n")[0])
    ap.add_argument("batch", type=Path)
    ap.add_argument("draft", type=Path)
    ap.add_argument("--allowlist", type=Path)
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parents[3]
    allowlist = align.load_allowlist((args.allowlist or repo / ALLOWLIST).read_text(encoding="utf-8"))
    ok, kept, failures = lint_rows(args.batch, args.draft, allowlist)
    stem = args.draft.name.removesuffix(".jsonl")
    out = args.draft.with_name(stem + ".ok.jsonl")
    write_jsonl(out, ok)
    write_jsonl(args.draft.with_name(stem + ".keep.jsonl"), kept)
    for ref, reasons in sorted(failures.items()):
        print(f"{ref}: {'; '.join(reasons)}")
    for row in kept:
        print(f"{row['ref']}: kept_english: {row['en']}")
    warned = warnings(args.batch, args.draft)
    for ref, found in sorted(warned.items()):
        print(f"{ref}: warning: {'; '.join(found)}")
    print(f"lint: {len(ok)} ok · {len(kept)} kept_english · {len(failures)} failed · {len(warned)} warned "
          f"→ {out.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
