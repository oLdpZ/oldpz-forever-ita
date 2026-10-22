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
from collections.abc import Iterable, Sequence
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


def mark_names(it: str, glossary: Iterable[Sequence[str]]) -> str:
    """`it` with every whole-word occurrence of a glossary term's Italian form marked `⟦en=it⟧`. Longest
    Italian form first (then longest English), never inside a marker already there, so a second call changes
    nothing. `glossary`: (en, it[, kind]) rows; a `classe` / `razza` row, or one holding the marker syntax, is
    skipped."""
    terms: dict[str, str] = {}
    for row in glossary:
        en, form, kind = row[0], row[1], (row[2] if len(row) > 2 else "")
        if not _usable(en, form, kind):
            continue
        if form not in terms or len(en) > len(terms[form]):
            terms[form] = en
    if not terms or not it:
        return it
    for form in sorted(terms, key=lambda f: (-len(f), -len(terms[f]), f)):
        word = re.compile(rf"(?<!{_WORD}){re.escape(form)}(?!{_WORD})")
        marker = f"{OPEN}{terms[form]}{SEP}{form}{CLOSE}"

        def put(text: str, word: re.Pattern[str] = word, marker: str = marker) -> str:
            return word.sub(lambda _m: marker, text)

        parts, at = [], 0
        for m in MARK.finditer(it):  # only the text between markers is searched
            parts += [put(it[at : m.start()]), m.group(0)]
            at = m.end()
        parts.append(put(it[at:]))
        it = "".join(parts)
    return it


def mark_from_english(it: str, en: str | None, matcher: _Finder | None) -> str:
    """`mark_names` with the glossary terms `en` holds (`glossary_it.Matcher.find`): no English or no
    glossary, no marker."""
    if matcher is None or not en or not it:
        return it
    return mark_names(it, matcher.find(en))
