"""Voice over rules: the scope, who speaks each line, the text a voice reads, and the fingerprint that says
whether a made audio file still matches its line. Pure: no database, no network.

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
from typing import Any

from wfj.core import names
from wfj.core.hashing import key as hash_key
from wfj.core.normalize import normalize_v1

# A scope names the file that lists its ids: quest ids, and `b <book key>` for a page of a book or a sign.
SCOPES: dict[str, str] = {
    "tirisfal": "pipeline/voice_tirisfal.txt",
    "orda": "pipeline/voice_orda.txt",
    "alleanza": "pipeline/voice_alleanza.txt",
    "iniziali": "pipeline/voice_iniziali.txt",
}
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
_SPLIT_PAIR = re.compile(r"<[^<>/]*/[^<>]*>")  # left after the pairs are resolved: words with spaces
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


def respell(text: str, table: Mapping[str, str]) -> str:
    """`text` with each whole word of `table` written as the voice must say it (voice.toml `[pronounce]`:
    "Lich" is read "lik" in Italian, "Litch" gives the soft ch). Only the transcript changes, never the
    shipped Italian."""
    for word, said in table.items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", said, text)
    return text


def text_hash(
    it: str, values: Sequence[str] = (), spoken: str | None = None, respelled: str | None = None
) -> str:
    """What a file's words were made from: the shipped Italian, the numbers filled into it, the spoken
    version, when the line has one, and the transcript, when a pronunciation respelled it."""
    payload = it
    if values:
        payload += "\x00" + ",".join(values)
    if spoken is not None:
        payload += "\x01" + spoken
    if respelled is not None:
        payload += "\x02" + respelled
    return it_hash(payload)


def speech_text(it: str, key: str, sex: str, values: Sequence[str] = (), spoken: str | None = None) -> str:
    """The text the voice reads, for a player of `sex` ("m" or "f"). A marked name becomes its Italian form,
    a `<a/b>` pair the form for `sex`, `{name}` the hero, `$B` a line break, `$N<k>` the k-th number of the
    line's English (`values`); a number only the game knows reads as "alcuni". Stage directions, colour codes,
    `%s` and page markup are dropped; a line that is nothing but a stage direction is refused: read without
    its brackets the direction would be spoken as a line. A line naming the player's class or race is read
    only from `spoken`, its spoken version. Any other markup is refused with the line's key: it would be read
    aloud as symbols."""
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
    # a pair of several words is not a pair: it would be taken for a stage direction and dropped unread
    split = _SPLIT_PAIR.search(text)
    if split:
        raise VoiceError(f"{key}: {split.group(0)!r}: a <male/female> pair takes one word on each side")
    spoken_text = _STAGE.sub("", text)
    if not _MARKUP.sub("", spoken_text).strip() and _MARKUP.sub("", text).strip():
        raise VoiceError(f"{key}: only a stage direction")
    bad = _MARKUP.search(spoken_text)
    if bad:
        raise VoiceError(f"{key}: markup {bad.group(0)!r} the voice cannot read")
    spoken_text = re.sub(r"[ \t]*\n[ \t]*", "\n", re.sub(r"[ \t]{2,}", " ", spoken_text)).strip()
    if not spoken_text:
        raise VoiceError(f"{key}: nothing left to read")
    return spoken_text


# The bracketed tags a transcript may carry: short English cues Gemini performs instead of reading. Kept
# short on purpose; any other bracket (an Italian cue, a stray bracket of the text) would be read aloud.
SPEECH_TAGS = frozenset(("sigh", "laughing", "whispering", "cough", "shouting", "crying", "gasp", "groan"))
_TAG = re.compile(r"\[([^\[\]]*)\]")


def tag_problem(transcript: str) -> str | None:
    """Why a transcript's brackets would be read aloud, or None: every `[...]` must be one of SPEECH_TAGS."""
    for m in _TAG.finditer(transcript):
        if m.group(1) not in SPEECH_TAGS:
            return f"tag {m.group(0)!r} is not one of the English tags {', '.join(sorted(SPEECH_TAGS))}"
    rest = _TAG.sub("", transcript)
    if "[" in rest or "]" in rest:
        return "a bracket that opens no tag would be read aloud"
    return None


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


def fingerprint(
    it_h: str, voice_id: str, gemini_voice: str, model: str, notes: str, sex: str, profile: str = ""
) -> str:
    """What a file was made from: the Italian hash, the roster voice, the engine's voice and model, the
    director's notes, the player's sex and the prompt's audio profile line (who the speaker is). A file is
    made again when any of them changes, so recasting one kind of speaker, or correcting one creature's
    profile, remakes only its lines."""
    fp = f"{it_h}|{voice_id}|{gemini_voice}|{model}|{hash_key(notes)}|{sex}"
    return f"{fp}|{hash_key(profile)}" if profile else fp


@dataclass(frozen=True)
class Job:
    """One audio file: `stem` is the file name without `.mp3`: the pack key for a line's main voice,
    `<key>_<voice>` or `<key>_f` for a variant. `voice` is a roster voice id, `sex` the player's."""

    stem: str
    key: str
    voice: str
    sex: str


# ---- who speaks a line -----------------------------------------------------------------------------------

_KEY = re.compile(r"\d+-(?:description|progress|completion)|[gb]-[0-9a-f]{16}")
_VOICE_ID = re.compile(r"[a-z0-9]+")


def gossip_id(en: str) -> str:
    """The gossip key of an English text, as the importer keys it (ADR-005)."""
    return hash_key(normalize_v1(en))


def quest_speakers(
    keys: Iterable[str],
    starters: Mapping[int, Sequence[int]],
    objects: set[int],
    enders: Mapping[int, Sequence[int]],
    others: dict[str, list[int]] | None = None,
) -> tuple[dict[str, int | str], list[str]]:
    """{pack key: creature id or narrator} for quest keys, and the conflicts reported. The offer is read by
    the creature that starts the quest; an object or item start (no creature) is the narrator. Progress and
    turn-in are read by the creature that ends it. Two creatures for one line: the lowest id is its main
    speaker, reported; the rest go into `others` when it is given (each may have a voice of its own)."""
    out: dict[str, int | str] = {}
    problems: list[str] = []
    for key in sorted(keys):
        quest_s, field = key.split("-", 1)
        quest = int(quest_s)
        who = list(starters.get(quest, []) if field == "description" else enders.get(quest, []))
        if not who:
            out[key] = NARRATOR
            if field != "description" or quest not in objects:
                problems.append(f"{key}: no creature in the database, narrator")
            continue
        if len(who) > 1:
            problems.append(f"{key}: creatures {who}, took {min(who)}")
            if others is not None:
                others[key] = sorted(set(who) - {min(who)})
        out[key] = min(who)
    return out, problems


def captured_speaker(names: Sequence[int | None]) -> int | str | None:
    """The speaker most submissions name for a window: a creature id, the narrator for an object (a shrine, a
    sign), or None when there are none. A tie goes to a creature, then the lowest id."""
    if not names:
        return None
    counts: dict[int | None, int] = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    best = max(counts.items(), key=lambda kv: (kv[1], kv[0] is not None, -(kv[0] or 0)))[0]
    return NARRATOR if best is None else best


def gossip_speakers(
    lines: Iterable[tuple[int, str]],
    collector: Mapping[str, Sequence[int]],
    shipped_keys: set[str],
    others: dict[str, list[int]] | None = None,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """{pack key: creature id} for the gossip lines of the given creatures that ship in Italian. A creature id
    the collector recorded in game for that line wins over the database (what the client served). Report:
    `conflict` (several creatures, lowest taken) and `missing` (English with no shipped Italian)."""
    by_key: dict[str, set[int]] = {}
    report: dict[str, list[str]] = {"conflict": [], "missing": []}
    for creature, en in lines:
        k = gossip_id(en)
        if k not in shipped_keys:
            report["missing"].append(f"g-{k} (creature {creature})")
            continue
        by_key.setdefault(k, set()).add(creature)
    out: dict[str, int] = {}
    for k, creatures in sorted(by_key.items()):
        recorded = list(collector.get(k, []))
        seen = sorted(set(recorded) & creatures) or sorted(recorded) or sorted(creatures)
        if len(seen) > 1:
            report["conflict"].append(f"g-{k}: creatures {seen}, took {seen[0]}")
        rest = sorted((set(recorded) | creatures) - {seen[0]})
        if rest and others is not None:
            others[gossip_key(k)] = rest
        out[gossip_key(k)] = seen[0]
    report["missing"] = sorted(set(report["missing"]))
    return out, report


_SIGNER = r"[A-Z][\w'.]*(?: [A-Z][\w'.]*){0,3}"
_SIGNATURE = re.compile(rf"^({_SIGNER})\s*$")
# "- Windan Shay", "-Baelog.", "--VanCleef", "-Thrall, Warchief of the Horde", "- Antonidas - Archmage"
_DASHED = re.compile(rf"^(?:--?|~|—|–)\s*({_SIGNER})\s*(?:(?:,| - ).*)?$")
_CLOSING = re.compile(r"^[^.!?]{1,40},$")  # "Your friend," "Sincerely," "With respect,"


def book_signature(en: str) -> str | None:
    """The name an English page is signed with: its last non-empty line, when that line is only a name. A
    dashed name counts, with one or two hyphens, an en or em dash or a tilde before it and a title after a
    comma or " - "; an undashed one must not read as a title ("The End", "REMEMBER"), and a single undashed
    word counts only under a closing line ("Your friend,")."""
    lines = [ln.strip() for ln in _BREAK.sub("\n", en).splitlines() if ln.strip()]
    if len(lines) < 2:  # a page that is only a name is a title or a label, not a signed text
        return None
    last = lines[-1]
    dashed = _DASHED.match(last)
    if dashed:
        return dashed.group(1).rstrip(".") or None
    m = _SIGNATURE.match(last)
    if not m:
        return None
    name = m.group(1).rstrip(".")
    if name.split()[0] in ("The", "A", "An") or name.isupper():
        return None
    if " " not in name and not _CLOSING.match(lines[-2]):
        return None
    return name or None


def book_speakers(
    pages: Mapping[str, str], names: Mapping[str, Sequence[int]], cast: Iterable[int]
) -> dict[str, int | str]:
    """{book key: reader} for book pages (key → English): the page's signer when exactly one creature of
    `cast` (the creatures that speak) has that name, else the book narrator (an unsigned page, a name no
    speaker has, or several)."""
    cast_ids = set(cast)
    out: dict[str, int | str] = {}
    for key, en in pages.items():
        who = [c for c in names.get(book_signature(en) or "", ()) if c in cast_ids]
        out[key] = who[0] if len(who) == 1 else BOOK_NARRATOR
    return out


def speaker_problems(speakers: Sequence[Mapping[str, Any]], voices: Sequence[Mapping[str, Any]]) -> list[str]:
    """`wfj validate` over data/voice/speakers.jsonl and voices.jsonl: shape, provenance, duplicates and,
    once a cast is written, a voice for every creature that speaks."""
    problems = _speaker_rows(speakers)
    has_voice: set[int] = set()
    for row in voices:
        c = row.get("creature")
        if not _creature_id(c):
            problems.append(f"voice voices: bad creature {c!r}")
            continue
        if c in has_voice:
            problems.append(f"voice voices {c}: duplicate")
        has_voice.add(c)
        for f in ("voice", "female"):
            v = row.get(f)
            if (f == "voice" or v is not None) and not (isinstance(v, str) and _VOICE_ID.fullmatch(v)):
                problems.append(f"voice voices {c}: {f} must be a roster voice id")
        if not isinstance(row.get("row"), str) or not row["row"]:
            problems.append(f"voice voices {c}: row must name the cast row that chose the voice")
        problems += _provenance(row, f"voice voices {c}")
    if voices:  # before the first cast no creature has a voice yet
        for row in speakers:
            for sp in (row.get("speaker"), *row.get("others", [])):
                if _creature_id(sp) and sp not in has_voice:
                    problems.append(f"voice speakers {row.get('key')}: creature {sp} has no voice row")
    return problems


def _speaker_rows(speakers: Sequence[Mapping[str, Any]]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for row in speakers:
        key = row.get("key")
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            problems.append(f"voice speakers: bad key {key!r}")
        elif key in seen:
            problems.append(f"voice speakers {key}: duplicate")
        seen.add(str(key))
        sp = row.get("speaker")
        if sp == BOOK_NARRATOR and not str(key).startswith("b-"):
            problems.append(f"voice speakers {key}: only a book page has the book narrator")
        elif not (sp in (NARRATOR, BOOK_NARRATOR) or _creature_id(sp)):
            problems.append(
                f"voice speakers {key}: speaker must be a creature id, {NARRATOR!r} or {BOOK_NARRATOR!r}"
            )
        others = row.get("others", [])
        if not isinstance(others, list) or not all(_creature_id(o) for o in others) or sp in others:
            problems.append(f"voice speakers {key}: others must be creature ids other than the speaker")
        problems += _provenance(row, f"voice speakers {key}")
    return problems


def _creature_id(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _provenance(row: Mapping[str, Any], label: str) -> list[str]:
    prov = row.get("provenance")
    if not isinstance(prov, dict):
        return [f"{label}: provenance must be an object"]
    p = []
    if not isinstance(prov.get("source"), str) or not re.fullmatch(r"[a-z0-9_-]+@\S+", prov["source"]):
        p.append(f"{label}: provenance source must be name@version")
    if not isinstance(prov.get("imported"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", prov["imported"]):
        p.append(f"{label}: provenance imported must be a date")
    return p
