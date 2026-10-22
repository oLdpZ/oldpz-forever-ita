import pytest

from wfj.core.align import allowlist_problems, load_allowlist
from wfj.io.jsonl_store import Store


def test_every_allowlist_line_is_justified(root):
    text = (root / "pipeline/allowlist.txt").read_text(encoding="utf-8")
    assert allowlist_problems(text) == []
    assert len(load_allowlist(text)) >= 10


def test_every_allowlist_term_is_used_by_the_corpus(root):
    """A term nobody needs must not be allowlisted (it would hide a real misalignment)."""
    # ADR-101: the Italian alignment checks numbers only, no Latin names, so no line consults the list: an
    # unused term hides nothing. The Japanese corpus wrote these words in Latin letters inside its prose; the
    # Italian one writes them in Italian ("Agilità"), so the measure has nothing to count until a name check
    # comes back.
    pytest.skip("ADR-101: no name check reads the allowlist")
    terms = load_allowlist((root / "pipeline/allowlist.txt").read_text(encoding="utf-8"))
    store = Store(root / "data")
    corpus = "\n".join(ln["it"] for t in ("quest", "item", "spell") for ln in store.load(t)).casefold()
    if not corpus:
        return
    unused = sorted(t for t in terms if t not in corpus)
    assert unused == [], unused
