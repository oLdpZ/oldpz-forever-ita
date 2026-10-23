"""Marked names (spec §8, "stile dei nomi"): both forms of a glossary name in the stored Italian.

A name of the official glossary (`pipeline/glossario_ufficiale.tsv`) that an Italian line carries is stored as
`⟦<english>=<italian>⟧` (`Porta queste pelli a ⟦Stormwind City=Roccavento⟧.`), and the addon shows one form
per the player's setting (`Core/Names.lua`, the Lua twin, proven by vectors/names_vectors.*). The separator
is `=` because `|` is the escape character of WoW text; a term holding `=`, `⟦` or `⟧` is never marked.

The pipeline writes the markers (`import draft`, `import official`), never the translator, and only for a term
the line's English holds (`mark_from_english`): the English decides which terms apply, and the Italian form
must be in the Italian as a whole word, case-sensitively (a name is written as the glossary writes it). Class
and race words (`classe`, `razza`) stay Italian in every style and are never marked. Every rule that reads
the Italian (`check`'s statuses, numbers, length) reads `resolve(it, "it")`, the text the player reads by
default; the English hash is untouched, so stale detection is unaffected.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Sequence
from typing import Protocol

OPEN, CLOSE, SEP = "⟦", "⟧", "="
# Lazy on both halves, like the Lua twin's `⟦(.-)=(.-)⟧` (⟦⟧ are multibyte: Lua cannot exclude them in a set)
MARK = re.compile(r"⟦(.*?)=(.*?)⟧", re.S)
STYLES = ("it", "en")
UNMARKED_KINDS = frozenset({"classe", "razza"})
_WORD = r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_]"
# Style "en": an English name starting "The " right after one of these (case-insensitive, a whole word, then
# one space) loses its "The ": "la The Bulwark" reads "la Bulwark". APOSTROPHE_ARTICLES take the apostrophe
# instead ("dall'The Den" → "dall'Den"). Twin of Core/Names.lua.
ARTICLES = frozenset({
    "il", "lo", "la", "i", "gli", "le", "del", "dello", "della", "dei", "degli", "delle", "al", "allo",
    "alla", "ai", "agli", "alle", "dal", "dallo", "dalla", "dai", "dagli", "dalle", "nel", "nello", "nella",
    "nei", "negli", "nelle", "sul", "sullo", "sulla", "sui", "sugli", "sulle", "col",
})
APOSTROPHE_ARTICLES = frozenset({"l", "dell", "all", "dall", "nell", "sull"})
APOSTROPHES = ("'", "’")
# the word before the marker: ASCII letters and anything outside ASCII (the Lua twin's `[%a\128-\255]`)
_LAST_WORD = re.compile(r"(?:[A-Za-z]|[^\x00-\x7f])+$")
# mark_names: the token for a held name while the search runs (private-use characters, which stored Italian
# never holds); every token is put back before the text is returned
_HOLD_OPEN, _HOLD_CLOSE = "", ""
_HOLD = re.compile(f"{_HOLD_OPEN}([0-9]+){_HOLD_CLOSE}")
_ENGLISH_GOES_ON = r"(?!['’][A-Za-z])(?! [A-Z])"
_TAKEN = re.compile(f"{MARK.pattern}|{_HOLD.pattern}", re.S)


class _Finder(Protocol):
    def find(self, text: str) -> list[list[str]]: ...


def has_marks(text: str | None) -> bool:
    return bool(text) and OPEN in text  # type: ignore[operator]


def resolve(text: str, style: str) -> str:
    """The text with each marker as its Italian (`it`) or English (`en`) form."""
    if style not in STYLES:
        raise ValueError(f"names: style must be one of {STYLES}, not {style!r}")
    if not has_marks(text):
        return text
    if style == "it":
        return MARK.sub(lambda m: m.group(2), text)
    return MARK.sub(lambda m: _english(m.group(1), text[: m.start()]), text)


def _after_article(before: str) -> bool:
    """`before` (the text up to a marker) ends with an Italian article and one space, or an elided one and its
    apostrophe."""
    if before.endswith(" "):
        word, articles = before[:-1], ARTICLES
    elif before.endswith(APOSTROPHES):
        word, articles = before[:-1], APOSTROPHE_ARTICLES
    else:
        return False
    m = _LAST_WORD.search(word)
    return bool(m) and m.group(0).lower() in articles


def _english(en: str, before: str) -> str:
    return en[4:] if en.startswith("The ") and _after_article(before) else en


def strip_marks(text: str) -> str:
    """The text the player reads by default: what every check of the Italian reads."""
    return resolve(text, "it")


def _usable(en: str, it: str, kind: str) -> bool:
    if kind in UNMARKED_KINDS or not en or not it or en == it:
        return False
    return not any(c in s for s in (en, it) for c in (OPEN, CLOSE, SEP))


def mark_names(it: str, glossary: Iterable[Sequence[str]], english_kinds: Collection[str] = ()) -> str:
    """`it` with every whole-word occurrence of a glossary term's Italian form marked `⟦en=it⟧`. Longest
    Italian form first (then longest English), never inside a marker already there, so a second call changes
    nothing. `glossary`: (en, it[, kind]) rows; a `classe` / `razza` row, or one holding the marker syntax, is
    skipped. A term of one of `english_kinds` (`creatura`: an NPC name the Italian left in English) is also
    found by its English form, marked with its Italian: both searches run together, longest first, so a name
    inside a longer one (`Defias Thug` in `Defias Thug Leader`) is never marked on its own. Such a term whose
    two forms agree (a longer NPC name with no Italian yet) is never marked but still taken first, so the
    names inside it stay as they are (`Peddlefeet` in `Kwee Q. Peddlefeet`)."""
    terms: dict[str, str] = {}
    english: dict[str, str] = {}
    held: set[str] = set()
    for row in glossary:
        en, form, kind = row[0], row[1], (row[2] if len(row) > 2 else "")
        if kind in english_kinds and en and en == form and not any(c in en for c in (OPEN, CLOSE, SEP)):
            held.add(en)
        if not _usable(en, form, kind):
            continue
        if form not in terms or len(en) > len(terms[form]):
            terms[form] = en
        if kind in english_kinds and en not in english:
            english[en] = form
    if not terms or not it:
        return it
    # search text → its marker; an Italian form wins over an English one spelt the same
    search = {en: f"{OPEN}{en}{SEP}{form}{CLOSE}" for en, form in english.items() if en not in terms}
    by_english = set(search)
    search.update({form: f"{OPEN}{en}{SEP}{form}{CLOSE}" for form, en in terms.items()})
    by_english -= set(terms)
    # a held name is set aside as a token (private-use characters around its index), put back at the end
    kept = [en for en in held if en not in search]
    search.update({en: f"{_HOLD_OPEN}{i}{_HOLD_CLOSE}" for i, en in enumerate(kept)})
    for text in sorted(search, key=lambda f: (-len(f), -len(search[f]), f)):
        # an English form is no name of its own where English goes on: a possessive or a longer English name
        # (`Hogger's Claw`, `Stonefield Farm`); a longer name that is a term was searched (and marked) first
        tail = _ENGLISH_GOES_ON if text in by_english else ""
        word = re.compile(rf"(?<!{_WORD}){re.escape(text)}(?!{_WORD}){tail}")
        marker = search[text]

        def put(chunk: str, word: re.Pattern[str] = word, marker: str = marker) -> str:
            return word.sub(lambda _m: marker, chunk)

        parts, at = [], 0
        for m in _TAKEN.finditer(it):  # only the text between markers (and held names) is searched
            parts += [put(it[at : m.start()]), m.group(0)]
            at = m.end()
        parts.append(put(it[at:]))
        it = "".join(parts)
    if kept:
        it = _HOLD.sub(lambda m: kept[int(m.group(1))], it)
    return it


def mark_from_english(
    it: str, en: str | None, matcher: _Finder | None, english_kinds: Collection[str] = ()
) -> str:
    """`mark_names` with the glossary terms `en` holds (`glossary_it.Matcher.find`): no English or no
    glossary, no marker. `english_kinds`: as `mark_names`."""
    if matcher is None or not en or not it:
        return it
    return mark_names(it, matcher.find(en), english_kinds)
