"""No Japanese ships: not one Hiragana, Katakana, CJK or full-width character anywhere in the addon folder.

One file is left out: `Data/Vectors.lua`, the shipped copy of the hash vectors (`/fita debug hash`), which must stay
byte for byte the upstream contract (`vectors/hash_vectors.*`, the Normalize / Hash twins) and so keeps its
Japanese and full-width test strings.
"""

import re
from pathlib import Path

ADDON = Path("addon/OldpZ_ForeverITA")
JAPANESE = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿豈-﫿＀-￯]")
TEXT_SUFFIXES = {".lua", ".toc", ".xml", ".md", ".txt"}
EXEMPT = {ADDON / "Data" / "Vectors.lua"}


def test_no_japanese_characters_in_the_addon(root: Path):
    hits = []
    files = [p for p in sorted((root / ADDON).rglob("*")) if p.is_file() and p.suffix in TEXT_SUFFIXES]
    assert len(files) > 50
    for path in files:
        rel = path.relative_to(root)
        if rel in EXEMPT:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if JAPANESE.search(line):
                hits.append(f"{rel}:{n}: {line.strip()[:80]}")
    assert hits == []
