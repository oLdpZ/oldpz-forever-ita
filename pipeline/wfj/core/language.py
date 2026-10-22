"""Is this Italian? At least one Latin letter, and not the English itself.

No stop-word heuristic: a short line ("Città", "Sì") is as Italian as a long one, and an Italian line may
keep an English proper name. What fails is text with no Latin letter at all (another script, only digits or
punctuation) and a line that is the English unchanged once both are normalized (`normalize_v1`).
"""

from __future__ import annotations

import re

from wfj.core.normalize import normalize_v1

LATIN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


def is_italian(text: str, english: str | None = None) -> bool:
    if not text.strip() or not LATIN.search(text):
        return False
    return english is None or normalize_v1(text) != normalize_v1(english)
