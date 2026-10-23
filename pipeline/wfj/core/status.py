"""The status decision table (docs/systems/pipeline.md, ADR-003, ADR-007). Pure.

decide() looks at one line, its English scope, and the current English hash, and returns what the
line's status, reasons, and checks should be, plus which conflict variant should be the line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from wfj.core import align, decisions, dedupe, language, markup, names, paragraphs, specifiers
from wfj.core import style as style_mod

NO_ENGLISH_ID = "no_english_id"
NOT_ITALIAN = "not_italian"
DUPLICATE_CONFLICT = "duplicate_conflict"
ALIGNMENT_FAILED = "alignment_failed"
NUMBERS_CHANGED = "numbers_changed"
TRUNCATED = "truncated"
SPECIFIERS_CHANGED = "specifiers_changed"
MARKUP_CHANGED = "markup_changed"  # colour tokens / line breaks / plural groups (core/markup.py)
RULED_REJECT = "ruled_reject"  # the only candidate carries `ruling: reject` and passes the rules
# Prose checked against its own English: names, numbers, completeness.
PROSE_KINDS = ("quest", "book", "objective", "area")  # objective and area keep their names


# A line of only dots and spaces (the draft lint's `_DOTS`): "...", "…".
DOTS = re.compile(r"[.…\s]+")


# English read from the client's own templates, where `$b<k>` is a value rather than a break
CLIENT_KINDS = frozenset({"item", "spell"})


@dataclass
class Scope:
    """The English a line is checked against. `fields` holds per-field English; `text` is the whole
    scope joined (quest: every field of the quest; item/spell: the name)."""

    # quest | item | spell | ui | gossip (the key is the English hash; no English text) | book | objective
    # | area
    kind: str
    fields: dict[str, str] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)  # per-field English hash from the store
    raw: dict[str, str] = field(default_factory=dict)  # per-field RAW English ($B markers intact)
    src: str = ""  # the first English line's source (gossip: GOSSIP_SRC), the fallback when a field has none
    srcs: dict[str, str] = field(default_factory=dict)  # per-field source (pfQuest + vmangos)
    # the fields whose English is only dots ("..."): their Italian may be only dots too ("……"), the
    # draft lint's rule. Set for gossip too, whose scope otherwise carries no English.
    dotted: frozenset[str] = frozenset()

    @property
    def text(self) -> str:
        return "\n".join(self.fields.values())

    @property
    def empty(self) -> bool:
        return not self.fields


@dataclass
class Decision:
    status: str
    reasons: list[str]
    checks: list[str]
    winner: int  # variant index that should be the line (0 = unchanged)


def _evaluate_ui(it: str, en: str) -> tuple[list[str], list[str]]:
    """The UI rules for one variant → (reasons, checks)."""
    # a UI template is filled with the client's values, so the Italian takes the same arguments.
    # No names / numbers / length: a UI string carries none of them (ADR-014).
    reasons: list[str] = []
    checks: list[str] = []
    try:
        has_specifiers = bool(specifiers.parse(en)) or "%" in it
    except ValueError:  # an unparseable template is a rejection below, never a crash
        has_specifiers = True
    if has_specifiers:
        checks.append("specifiers")
    bad = specifiers.mismatch(en, it)
    if bad:
        reasons.append(f"{SPECIFIERS_CHANGED}:{bad}")
    # the client prints colour codes and line breaks as they are; the Italian keeps the same.
    bad_markup = markup.mismatch(en, it)
    if bad_markup:
        reasons.append(f"{MARKUP_CHANGED}:{bad_markup}")
    return reasons, checks


def _evaluate(
    it: str,
    field_name: str,
    scope: Scope,
    provenance: dict[str, Any] | None = None,
    accepted: bool = False,
) -> tuple[list[str], list[str]]:
    """Rules 3, 5, 6 for one variant → (reasons, checks). `provenance` feeds the structural completeness
    rule (a first-paragraph-only layer, ADR-011). `accepted`: the variant carries
    `ruling: accept`; a line ruled to stay as its English ("NEW", "%d FPS", a name such as `Umbrinoth`) is
    not `not_italian`. A marked name (`⟦Stormwind City=Roccavento⟧`, spec §8) is judged as the Italian the
    player reads by default (`names.strip_marks`): its English half is no word, number or length of the
    line."""
    it = names.strip_marks(it)
    wordless = scope.kind == "ui" and _no_words(scope.raw.get(field_name))
    # any line may carry the same ruling: a label that is only a name, a class or profession name, an
    # internal string, a line in a made-up language or a quest title that is a proper name ships as the
    # English it is, without the missing marker. Without it, Italian is a line with a Latin letter that is
    # not its English (`language.is_italian`; gossip has no English text to compare).
    kept_english = accepted
    dots = field_name in scope.dotted and DOTS.fullmatch(it) is not None
    english = scope.raw.get(field_name, scope.fields.get(field_name))
    if english is None and scope.kind in CLIENT_KINDS:  # an item / spell line that is only its name
        english = scope.fields.get("name")
    if not language.is_italian(it, english) and not wordless and not kept_english and not dots:
        return [NOT_ITALIAN], []
    if scope.kind == "ui":
        return _evaluate_ui(it, scope.raw.get(field_name, ""))
    reasons: list[str] = []
    checks: list[str] = []
    if scope.kind == "book":
        # a book page is prose checked like a quest's; its SimpleHTML renders the page's HTML tags, so
        # the Italian keeps them in order.
        bad_html = markup.html_mismatch(scope.raw.get(field_name, ""), it)
        if bad_html:
            reasons.append(f"{MARKUP_CHANGED}:html:{bad_html}")
    if scope.kind not in PROSE_KINDS:
        # ADR-007: item/spell text was translated from rendered tooltip lines; the only offline English
        # is the name, which is not a scope for the description. The runtime gate does the real check.
        # Gossip: no consulted English text exists; the key is the English (ADR-017).
        return reasons, checks
    # Quest fields and book pages: numbers, completeness. No name check (ADR-101): every Italian word is
    # Latin, so `align.check_names` would read each one as a name the English must hold; name consistency is
    # the official glossary's lint.
    # Numbers are only checked for fields that have their own English (completion/progress do not
    # exist in pfQuest; their counts would be compared against a different field).
    if field_name in scope.fields:
        d_checked, d_missing = align.check_numbers(it, scope.text)
        if d_checked:
            checks.append("numbers")
        reasons += [f"{NUMBERS_CHANGED}:{m}" for m in d_missing]
    # Completeness (ADR-011): a first-paragraph-only translation is not a translation. Only for prose
    # fields that have their own English; titles and fields without pfQuest English are not length-checked.
    if field_name in scope.fields and field_name != "title":
        raw = scope.raw.get(field_name, scope.fields[field_name])
        structural = paragraphs.first_paragraph_only(provenance or {})
        cut, jp, ep = paragraphs.is_truncated(
            it, raw, scope.fields[field_name], structural=structural, client=scope.kind in CLIENT_KINDS
        )
        if ep >= 2 or cut:  # `checks` records what had something to compare
            checks.append("length")
        if cut:
            reasons.append(f"{TRUNCATED}:{jp}/{ep}")
    return reasons, checks


# a named colour code (`|cnPURE_BLUE_COLOR:`) is markup, not words
_NAMED_COLOUR = re.compile(r"\|cn[A-Z_]+:")


def _no_words(en: str | None) -> bool:
    """A UI template with no words outside its specifiers ("(%s)") has nothing to translate, so its
    Italian form need carry no Latin letter either. Nor outside its named colour codes (the gossip
    option's quest prepend, "|cnPURE_BLUE_COLOR:%s|r %s")."""
    if en is None:
        return False
    bare = specifiers.SPEC.sub("", _NAMED_COLOUR.sub("", markup.TOKEN.sub("", en)))
    return not re.search(r"[A-Za-z]", bare)


# Who wrote a variant, best first: Blizzard's own Italian (`official`, the text the retail client shows for
# the same English), a hand fix here (ADR-012), an imported named translator, a model (ADR-014). A correction
# of an official line wins only with `ruling: accept`.
CLASS_RANK = {decisions.OFFICIAL: 0, decisions.CORRECTION: 1, "human": 2, decisions.MACHINE: 3}


def _rank(c: dedupe.Candidate, field_name: str, scope: Scope) -> tuple[int, ...]:
    """Tie-break key (lower wins): hand-written before machine (a `correction` first, since a person fixed
    this text, ADR-012; then an imported `human` translation; then a `machine` draft, ADR-014), then the
    variant covering more English paragraphs, then (between machine drafts) the higher style guide version and
    the newer import, then source priority, then a named translator over a community label (ADR-011 §4).
    Only variants that pass every rule are ranked."""
    authored = CLASS_RANK.get(str(c.provenance.get("class")), len(CLASS_RANK))
    covered = 0
    if field_name in scope.fields and field_name != "title":
        covered = paragraphs.completeness(
            c.it, scope.raw.get(field_name, scope.fields[field_name]), client=scope.kind in CLIENT_KINDS
        )
    # Between machine drafts, the draft written under the newer style guide wins (a `-sg<N>` re-draft
    # replaces the older-version draft beside it), and between two drafts of the same version the newer
    # import, instead of tying into a duplicate_conflict that un-ships the line.
    style = newer = 0
    if decisions.is_machine(c.provenance):
        style = -style_mod.source_version(c.provenance)
        newer = -int(str(c.provenance.get("imported", "0")).replace("-", "") or 0)
    return (authored, -covered, style, newer, *dedupe.source_rank(c.provenance))


def _machine_barred(cands: list[dedupe.Candidate], c: dedupe.Candidate) -> bool:
    """Machine output never replaces a hand-written translation without an explicit, logged
    decision. A machine variant on a line that has a `human` or `correction` variant may win only with
    `ruling: accept`."""
    if not decisions.is_machine(c.provenance):
        return False
    if isinstance(c.ruling, dict) and c.ruling.get("ruling") == "accept":
        return False
    # A hand-written variant a person ruled `reject` no longer protects the line.
    return any(decisions.is_hand_written(o.provenance) and not _rejected(o) for o in cands)


def _accepted(c: dedupe.Candidate) -> bool:
    return isinstance(c.ruling, dict) and c.ruling.get("ruling") == "accept"


def _rejected(c: dedupe.Candidate) -> bool:
    return isinstance(c.ruling, dict) and c.ruling.get("ruling") == "reject"


def decide(
    line: dict[str, Any],
    scope: Scope | None,
    allowlist: set[str],  # noqa: ARG001 -- unread since ADR-101 (no name check); kept for callers
    current_hash: str | None,
    includes_changed: bool = False,
) -> Decision:
    """`includes_changed`: the English of a spell this item / spell template splices in has changed
    since the line was checked: the line the player reads changed, so the line is stale like a change to its
    own English."""
    field_name = line["field"]
    if scope is None or scope.empty:
        return Decision("rejected", [NO_ENGLISH_ID], [], 0)
    cands = dedupe.variants(line)
    # A barred machine variant is not a candidate at all, so a lone failing hand-written variant is rejected
    # with its own reasons exactly as before any draft existed.
    eligible = [c for c in cands if not _machine_barred(cands, c)]
    results = {
        c.index: _evaluate(c.it, field_name, scope, c.provenance, _accepted(c)) for c in eligible
    }
    passes = lambda c: not results[c.index][0]  # noqa: E731
    rank = lambda c: _rank(c, field_name, scope)  # noqa: E731
    if len(eligible) == 1 and _rejected(eligible[0]):
        # A reject ruling is permanent: the ruled text is never a candidate again, even when it
        # later passes the rules (new English, an allowlist entry, a rule change). The line ships nothing and
        # keeps its own reasons, or `ruled_reject` when the text passes. With several candidates,
        # `dedupe.resolve` already leaves rejected variants out of the passing set.
        only = eligible[0]
        reasons, checks = results[only.index]
        return Decision("rejected", reasons or [RULED_REJECT], checks, only.index)
    if len(eligible) == 1:
        winner: int | None = eligible[0].index
    else:
        winner = dedupe.resolve(eligible, passes, priority=True, rank=rank)
    if winner is None:
        return Decision("rejected", [DUPLICATE_CONFLICT], [], 0)
    reasons, checks = results[winner]
    if dedupe.tiebroken(eligible, passes, winner):
        checks = [*checks, "tiebreak"]
    if reasons:
        return Decision("rejected", reasons, checks, winner)
    prior = (line.get("english") or {}).get("hash")
    # an NPC name or title (`unit`) is plain text checked against its own English, with no client template or
    # live value to gate: trusted like a UI string
    if scope.kind not in (*PROSE_KINDS, "ui", "gossip", "unit"):
        # Item / spell (ADR-007): never checked offline, so never trusted. Once the English it was
        # checked against changes, it is stale: shipped, still gated in-game, shown with the stale marker.
        if (prior and current_hash and prior != current_hash) or includes_changed:
            return Decision("stale", [], checks, winner)
        return Decision("unaligned", [], checks, winner)
    if prior and current_hash and prior != current_hash:
        return Decision("stale", [], checks, winner)
    return Decision("trusted", [], checks, winner)
