"""The voice addon's own files (ADR-061). Deterministic text.

The pack folder (OldpZ_ForeverITA_Voce, or a pack of voice-packs.toml, OldpZ_ForeverITA_Voce_<suffix>)
holds its TOC, Register.lua, LEGGIMI.txt and Sound/. It depends on the main addon and hands
it one table through the main addon's single global, `OldpZ_ForeverITA_RegisterVoice`. Format 3: each line is
{ file name, Italian hash, seconds, f = { file name, seconds }, v = { [voice id] = { file name, seconds } } };
`f` is the take for a female character (a line that names the player or picks a word by sex), `v` is there
only for a line several differently cast creatures say, and `creatures` maps each speaker of such a line to
its voice id ({ m = male voice, f = female voice } for a creature shown as both). The addon plays a file only
when the hash equals the hash of the Italian it ships.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from wfj.emit.lua_writer import lua_string

FOLDER = "OldpZ_ForeverITA_Voce"
FORMAT = 3
TITLE = "oLd_pZ Forever - Voci italiane"
ICON = "Interface\\AddOns\\OldpZ_ForeverITA\\Media\\icon"
AUTHOR = "oLd_pZ"


@dataclass
class Entry:
    """One line of the pack: the male (or only) take, the female take of the main voice, and the takes of the
    other voices (each with its own female take)."""

    file: str
    hash: str
    seconds: float
    female: tuple[str, float] | None = None
    voices: dict[str, tuple[str, float, tuple[str, float] | None]] = field(default_factory=dict)


def title_of(words: str | None = None) -> str:
    """The pack's title: the voice's, with what the pack holds in brackets ("livelli 1-20")."""
    return f"{TITLE} ({words})" if words else TITLE


def toc_text(interface: str, version: str, title: str = TITLE) -> str:
    notes = "Voci italiane dei PNG per oLd_pZ Forever - Traduzione Italiana, che serve per sentirle."
    return "\n".join([
        f"## Interface: {interface}",
        f"## Title: {title}",
        f"## Notes: {notes}",
        f"## IconTexture: {ICON}",
        "## Dependencies: OldpZ_ForeverITA",
        f"## Author: {AUTHOR}",
        f"## Version: {version}",
        "",
        "Register.lua",
        "",
    ])


def _take(file: str, seconds: float, extra: str = "") -> str:
    return f"{{ {lua_string(file)}, {seconds:.1f}{extra} }}"


def _line(key: str, e: Entry) -> str:
    parts = [lua_string(e.file), lua_string(e.hash), f"{e.seconds:.1f}"]
    if e.female:
        parts.append(f"f = {_take(*e.female)}")
    if e.voices:
        v = ", ".join(
            f"[{lua_string(vid)}] = {_take(f, s, f', f = {_take(*fem)}' if fem else '')}"
            for vid, (f, s, fem) in sorted(e.voices.items())
        )
        parts.append(f"v = {{ {v} }}")
    return f"    [{lua_string(key)}] = {{ {', '.join(parts)} }},"


def _creature(c: int, v: str | tuple[str, str]) -> str:
    if isinstance(v, tuple):
        return f"    [{c}] = {{ m = {lua_string(v[0])}, f = {lua_string(v[1])} }},"
    return f"    [{c}] = {lua_string(v)},"


def register_text(
    lines: Mapping[str, Entry], creatures: Mapping[int, str | tuple[str, str]] | None = None,
    folder: str = FOLDER,
) -> str:
    """`lines`: {pack key: Entry}; `creatures`: {creature id: voice id or (male, female)}. Written sorted."""
    body = [_line(key, e) for key, e in sorted(lines.items())]
    who = [_creature(c, v) for c, v in sorted((creatures or {}).items())]
    return "\n".join([
        "-- Generato da wfj voice pack. Non modificare.",
        "-- Un addon principale troppo vecchio non ha la funzione di registrazione: il pacchetto resta muto.",
        "if not OldpZ_ForeverITA_RegisterVoice then return end",
        "OldpZ_ForeverITA_RegisterVoice({",
        f"  format = {FORMAT},",
        f"  folder = {lua_string(folder)},",
        "  lines = {",
        *body,
        "  },",
        "  creatures = {",
        *who,
        "  },",
        "})",
        "",
    ])


def readme_text(count: int, version: str, folder: str = FOLDER, title: str = TITLE) -> str:
    split = [] if folder == FOLDER else [
        "Le voci sono divise in più pacchetti (OldpZ_ForeverITA_Voce_...): uno per fascia di livello delle",
        "missioni e uno per libri, dialoghi e missioni senza livello. Installa quelli che vuoi: insieme",
        "funzionano come uno solo.",
        "",
    ]
    return "\n".join([
        title,
        "",
        "Le voci italiane dei PNG per oLd_pZ Forever - Traduzione Italiana (OldpZ_ForeverITA), l'addon",
        "principale: senza di esso questo pacchetto non suona nulla. Installa la cartella",
        f"{folder} in Interface\\AddOns accanto a OldpZ_ForeverITA.",
        "",
        *split,
        f"Versione {version}. Contiene {count} battute, dette dal testo italiano che l'addon mostra: se il",
        "testo di una battuta cambia, quella battuta resta muta finché non esce una voce nuova.",
        "",
        "Crediti",
        "- Voci generate con Google Gemini TTS.",
        "- Testi e addon: oLd_pZ.",
        "",
        "Togliere questo pacchetto lascia l'addon principale com'era.",
        "",
    ])
