"""Voice over rules: the scope, the text a voice reads, and the fingerprint that says whether a made audio
file still matches its line. Pure: no database, no network.

A line's pack key is the file name without `.mp3`: `<quest id>-<field>` for a quest field, `g-<gossip key>`
for a gossip line, `b-<book key>` for a book page. Audio is matched to its Italian by `it_hash`, the hash of
the Italian exactly as the addon ships it (markers and placeholders intact), so the addon can refuse audio
made from older Italian.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wfj.core import names
from wfj.core.hashing import key as hash_key

# A scope names the file that lists its ids: quest ids, and `b <book key>` for a page of a book or a sign.
SCOPES: dict[str, str] = {"tirisfal": "pipeline/voice_tirisfal.txt"}
# description is the offer the quest giver reads, progress and completion the turn-in NPC's lines
FIELDS = ("description", "progress", "completion")
NARRATOR = "narrator"
BOOK_NARRATOR = "book-narrator"
SEXES = ("m", "f")
# The pack is made before anyone plays: it cannot know the name, so the player is the hero.
HERO = {"m": "eroe", "f": "eroina"}

_NAME = re.compile(r"\{name\}")
_SPOKEN_ONLY = re.compile(r"\{(?:class|race)\}")
# `schiav<o/a>`, `<un/una>`, `<eroe/eroina>`: the masculine, then the feminine form. No spaces and no quotes,
# so an HTML tag with a slash (`<IMG src="x"/>`) is not a pair.
_PAIR = re.compile(r"<([^<>/\s\"=]+)/([^<>/\s\"=]+)>")
# Page markup a book carries (`<IMG .../>`, `<P>`): drawn, not read.
_HTML = re.compile(r"</?(?:IMG|P|BR|H[1-6])\b[^<>]*>", re.I)
# What is left between angle brackets once the pairs are resolved is a stage direction ("<Trevan sorride.>")
_STAGE = re.compile(r"<[^<>]*>")
_COLOUR = re.compile(r"\|c[0-9A-Fa-f]{8}|\|r")
_ENTITY = re.compile(r"%s")
_BREAK = re.compile(r"\$[bB]")
_FILL = re.compile(r"\$N(\d+)")
_WORLD_STATE = re.compile(r"\$\d+[wW]")  # a number the server fills in: not known when the audio is made
_MARKUP = re.compile(r"[{}<>$|]")
_SCOPE_BOOK = re.compile(r"b ([0-9a-f]{16})")
_UNKNOWN_NUMBER = "alcuni"


class VoiceError(ValueError):
    """A line the voice must not read as it stands."""


def quest_key(quest: int, field: str) -> str:
    return f"{quest}-{field}"


def gossip_key(key: str) -> str:
    return f"g-{key}"


def book_key(key: str) -> str:
    return f"b-{key}"


def it_hash(it: str) -> str:
    return hash_key(it)


def needs_variants(it: str) -> bool:
    """True when the player's sex changes the words read: `{name}` (eroe / eroina) or a `<a/b>` pair."""
    return bool(_NAME.search(it) or _PAIR.search(it))


def needs_spoken(it: str) -> bool:
    """True when the line names the player's class or race: the voice reads it only from a spoken version."""
    return bool(_SPOKEN_ONLY.search(it))


_LIVE_NUMBER = re.compile(r"[\d.,]+")


def live_values(en: str) -> list[str]:
    """The numbers the addon fills a line's `$N<k>` with, from its English: every run of digits, dots and
    commas not touching a Latin letter, commas dropped, and "A to B" joined as "da A a B". A port of
    Core/Align.lua `Align.values`, so the audio says the number the window shows."""
    en = _BREAK.sub("\n", en)  # the client shows $B as a line break, which ends the letter before a number
    out: list[str] = []
    last_end = None
    for m in _LIVE_NUMBER.finditer(en):
        s, e = m.start(), m.end()
        if (s > 0 and en[s - 1].isascii() and en[s - 1].isalpha()) or (
            e < len(en) and en[e].isascii() and en[e].isalpha()
        ):
            continue
        v = m.group(0).replace(",", "").strip(".")
        if not v:
            continue
        if last_end is not None and en[last_end:s] == " to ":
            out[-1] = f"da {out[-1]} a {v}"
        else:
            out.append(v)
        last_end = e
    return out


def text_hash(it: str, values: Sequence[str] = (), spoken: str | None = None) -> str:
    """What a file's words were made from: the shipped Italian, the numbers filled into it and the spoken
    version, when the line has one."""
    payload = it
    if values:
        payload += "\x00" + ",".join(values)
    if spoken is not None:
        payload += "\x01" + spoken
    return it_hash(payload)


def speech_text(it: str, key: str, sex: str, values: Sequence[str] = (), spoken: str | None = None) -> str:
    """The text the voice reads, for a player of `sex` ("m" or "f"). A marked name becomes its Italian form,
    a `<a/b>` pair the form for `sex`, `{name}` the hero, `$B` a line break, `$N<k>` the k-th number of the
    line's English (`values`); a number only the game knows reads as "alcuni". Stage directions, colour codes,
    `%s` and page markup are dropped (a line that is nothing but a stage direction is read without its
    brackets). A line naming the player's class or race is read only from `spoken`, its spoken version. Any
    other markup is refused with the line's key: it would be read aloud as symbols."""
    if sex not in SEXES:
        raise VoiceError(f"{key}: sex must be one of {SEXES}, not {sex!r}")
    if spoken is None and needs_spoken(it):
        raise VoiceError(f"{key}: names the player's class or race and has no spoken version")

    def number(m: re.Match[str]) -> str:
        k = int(m.group(1))
        return values[k - 1] if 1 <= k <= len(values) else _UNKNOWN_NUMBER

    text = names.resolve(it if spoken is None else spoken, "it")
    text = _PAIR.sub(lambda m: m.group(1 if sex == "m" else 2), text)
    text = _NAME.sub(HERO[sex], text)
    text = _WORLD_STATE.sub(_UNKNOWN_NUMBER, _FILL.sub(number, _BREAK.sub("\n", text)))
    text = _ENTITY.sub("", _COLOUR.sub("", _HTML.sub("", text)))
    spoken_text = _STAGE.sub("", text)
    if not _MARKUP.sub("", spoken_text).strip():
        spoken_text = re.sub(r"[<>]", "", text)
    bad = _MARKUP.search(spoken_text)
    if bad:
        raise VoiceError(f"{key}: markup {bad.group(0)!r} the voice cannot read")
    spoken_text = re.sub(r"[ \t]*\n[ \t]*", "\n", re.sub(r"[ \t]{2,}", " ", spoken_text)).strip()
    if not spoken_text:
        raise VoiceError(f"{key}: nothing left to read")
    return spoken_text


def read_scope_file(path: Path) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """(quest ids, book page keys) a scope file lists: one id per line, `b <key>` for a book page, `#` starts
    a comment. Each is sorted; a bad or repeated line is refused with the file's name and line."""
    quests: set[int] = set()
    books: set[str] = set()
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        book = _SCOPE_BOOK.fullmatch(line)
        if book:
            if book.group(1) in books:
                raise VoiceError(f"{path.name}:{n}: {line!r} is listed twice")
            books.add(book.group(1))
        elif line.isascii() and line.isdigit() and int(line) > 0:
            if int(line) in quests:
                raise VoiceError(f"{path.name}:{n}: {line!r} is listed twice")
            quests.add(int(line))
        else:
            raise VoiceError(f"{path.name}:{n}: not a quest id or `b <book key>`: {line!r}")
    return tuple(sorted(quests)), tuple(sorted(books))


def fingerprint(it_h: str, voice_id: str, gemini_voice: str, model: str, notes: str, sex: str) -> str:
    """What a file was made from: the Italian hash, the roster voice, the engine's voice and model, the
    director's notes and the player's sex. A file is made again when any of them changes, so recasting one
    kind of speaker remakes only its lines."""
    return f"{it_h}|{voice_id}|{gemini_voice}|{model}|{hash_key(notes)}|{sex}"


@dataclass(frozen=True)
class Job:
    """One audio file: `stem` is the file name without `.mp3`: the pack key for a line's main voice,
    `<key>_<voice>` or `<key>_f` for a variant. `voice` is a roster voice id, `sex` the player's."""

    stem: str
    key: str
    voice: str
    sex: str


def in_step(
    file_jobs: Iterable[Job], lines: Mapping[str, str], roster: Mapping[str, Mapping[str, str]],
    audio: Mapping[str, Mapping[str, str]], values: Mapping[str, Sequence[str]] | None = None,
    spoken: Mapping[str, str] | None = None,
) -> dict[str, list[str]]:
    """The audio record against what the files must be now: `missing` (no record), `stale` (made from other
    Italian, another voice or other notes). Empty lists: voice is in step with the translation. `roster` maps
    a voice id to its `gemini_voice`, `model` and `notes`; `values` and `spoken` are per line key."""
    out: dict[str, list[str]] = {"missing": [], "stale": []}
    for j in file_jobs:
        rec = audio.get(j.stem)
        if rec is None:
            out["missing"].append(j.stem)
            continue
        r = roster[j.voice]
        want = fingerprint(
            text_hash(lines[j.key], (values or {}).get(j.key, ()), (spoken or {}).get(j.key)),
            j.voice, r["gemini_voice"], r["model"], r["notes"], j.sex,
        )
        if rec.get("fingerprint") != want:
            out["stale"].append(j.stem)
    return out
