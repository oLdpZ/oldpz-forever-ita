"""The word readings / glosses, the bundled Italian font and the Italian predecessor importers are gone
(ofi Task 2): nothing in the addon or the pipeline names them any more. The voice over came back as a
module of ours, but the Japanese engine and its addon (`aivis`, `WoWForeverJapanese`) did not.

The game's own API carries the word "Voice" (voice chat, text to speech): those lines name Blizzard frames
and strings, not a module of ours, and are allowed by `_GAME_VOICE`. UI/Speech.lua and UI/TextToSpeech.lua
stay (speech bubbles and the text-to-speech window), so they are not scanned."""

import re
from pathlib import Path

REMOVED = re.compile(r"Readings|Glosses|import_predecessor|ipagui")
# Blizzard identifiers and strings that hold "Voice": voice chat, the Voice settings page, text to speech.
_GAME_VOICE = re.compile(
    r"VoiceChat|VOICE_CHAT|Blizzard_VoiceToggleButton|TtsVoice|Voices|AlternateVoice|VoiceOptions"
    r"|Voice: \\\"Magic debuff|the Voice page's service choice|fitVoiceLine|tipVoice"
)
KEPT = {Path("addon/OldpZ_ForeverITA/UI/Speech.lua"), Path("addon/OldpZ_ForeverITA/UI/TextToSpeech.lua")}
GENERATED = ("addon", "OldpZ_ForeverITA", "Data")
GONE_JAPANESE = re.compile(r"aivis|WoWForeverJapanese")
SUFFIXES = {".lua", ".xml", ".toc", ".py", ".html", ".toml", ".txt", ".json", ".md"}


def _hits(root: Path, gone: re.Pattern[str], allowed: re.Pattern[str] | None = None) -> list[str]:
    hits = []
    for top in ("addon", "pipeline/wfj"):
        for path in sorted((root / top).rglob("*")):
            rel = path.relative_to(root)
            if not path.is_file() or path.suffix not in SUFFIXES or rel in KEPT or "__pycache__" in rel.parts:
                continue
            if rel.parts[:3] == GENERATED:  # the shipped text (an item may be named "Voice …"), not code
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if gone.search(line) and not (allowed and allowed.search(line)):
                    hits.append(f"{rel}:{n}: {line.strip()[:120]}")
    return hits


def test_no_reference_to_removed_modules(root: Path):
    hits = _hits(root, REMOVED, _GAME_VOICE)
    assert hits == [], f"{len(hits)} line(s) still name a removed module:\n" + "\n".join(hits[:60])


def test_no_japanese_voice_engine_or_addon(root: Path):
    hits = _hits(root, GONE_JAPANESE)
    assert hits == [], f"{len(hits)} line(s) still name the Japanese voice:\n" + "\n".join(hits[:60])
