"""How much of the game ships in Italian: `docs/operations/coverage.md`, generated.

Measured from the English the Forever client serves (`data/english/`), not from the Italian store
(`wfj stats` counts every stored line, including post-Vanilla quests the client never shows), and never from a
list of what a player is likely to see: every served line of a surface counts. A line with nothing to
translate counts as done: a name-only objective / area text (`pipeline/objective_names.txt` /
`area_names.txt`), a placeholder quest, a picture-only book page.

The report also counts the served-text inventory (`pipeline/served_columns.txt` with
`pipeline/served_dispositions.txt`): every text column the client ships, by disposition, so a column left out
is a counted row with its reason.

A served line that has neither shipped Italian nor a stated reason (a name list, nothing to translate,
English still waiting on the Forever tables, a status with its reason) is a gap: `gaps` counts them and
`tests/python/test_coverage.py` fails on any.

    python -m wfj.dev.coverage [--out ../docs/operations/coverage.md] [--build <forever build>]
    (from pipeline/)
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from wfj.core import align
from wfj.dev import counts as readme_counts
from wfj.dev import served_dispositions
from wfj.dev.served_columns import inventory_build, read_inventory
from wfj.dev.translate_batch import (
    AREA_NAMES,
    OBJECTIVE_NAMES,
    has_prose,
    objective_names,
    read_kept,
    undraftable,
)
from wfj.emit.lua_writer import shipped
from wfj.io.jsonl_store import Store
from wfj.io.wdb import PLACEHOLDER_TITLE
from wfj.paths import data_root

# the fields a player reads per type (quest `area` is its own type; item `name` stays English)
SURFACE_FIELDS: dict[str, tuple[str, ...]] = {
    "quest": ("title", "objectives", "description", "progress", "completion"),
    "gossip": ("text",),
    "book": ("text",),
    "objective": ("text",),
    "area": ("text",),
    "item": ("description",),
    "spell": ("description", "aura"),
    "ui": ("text",),
    "unit": ("name", "subname"),
}
LABELS = {
    "quest": "Quest text",
    "gossip": "NPC dialogue (gossip, speech)",
    "book": "Book / letter pages",
    "objective": "Quest objective lines",
    "area": "Exploration / event objectives",
    "item": "Item descriptions",
    "spell": "Spell tooltips + auras",
    "ui": "Interface strings",
    "unit": "NPC names",
}
NAMES_LISTS = {"objective": OBJECTIVE_NAMES, "area": AREA_NAMES}
_TAG = re.compile(r"<[^>]*>")
_WORD = re.compile(r"[A-Za-z]{2,}")


def nothing_to_translate(type_: str, en: str, title: str | None, field: str = "") -> str | None:
    """Why a line has nothing to translate, or None: a placeholder quest (`<UNUSED>`, `<NYI>`, `REUSE`, never
    drafted), a book page that is "Missing Text", only pictures / markup, or a cipher, and a quest or book
    line
    that is a bare label (`has_prose`: no lower-case word, token or sentence punctuation: a name and a colon,
    a name and two years, "Log"). A quest title is never a bare label: titles are written in title case."""
    if type_ == "quest" and title is not None and PLACEHOLDER_TITLE.search(title):
        return "placeholder quest (never shown)"
    if type_ == "book":
        text = _TAG.sub(" ", en)
        if text.strip().lower() in ("missing text", ""):
            return "Missing Text / picture-only page"
        if not _WORD.search(text) or re.fullmatch(r"[\s01]+", text) or re.fullmatch(r"[\sOo]+", text):
            return "picture-only or cipher page"
        if not has_prose(text):
            return "a bare label: names and numbers only (ships as the English)"
    if type_ == "quest" and field != "title" and not has_prose(en):
        return "a bare label: a name or a one-word placeholder (ships as the English)"
    if type_ in ("item", "spell") and "$@null" in en and not align.NULL.sub("", en).strip():
        return "a template that prints nothing (`$@null`)"  # spell 348779, which exists to be included
    return None


# why a tooltip template cannot be drafted, in the reader's words: one class per reason `translate_batch`
# gives, never one row per spell id
_TEMPLATE_REASONS = {
    "missing_included_spell": "includes a spell the Forever tables do not hold",
    "unsupported_code:$@auracaster": "names the aura's caster, which only the game knows",
    "unsupported_code:$@spellaura": "includes an aura without saying which spell's",
    "too_many_variants": "has too many optional parts for one translation",
    "branches_indistinguishable": "has wordings the addon could not tell apart on screen",
    "unclosed_branch": "has a conditional the pipeline cannot read",
    "uncountable": "does not say how many values it prints",
}


def template_reason(reason: str) -> str:
    """The plain reason class for a `translate_batch.undraftable` reason (`missing_included_spell:998` is
    the class `missing_included_spell`)."""
    plain = _TEMPLATE_REASONS.get(reason) or _TEMPLATE_REASONS.get(reason.split(":", 1)[0])
    if plain:
        return plain
    if reason.startswith("unsupported_code:"):
        return "uses a template code the pipeline cannot place (" + reason.split("$@", 1)[-1] + ")"
    return "cannot be drafted (" + reason.replace(":", " ").replace("$", "") + ")"


UI_EXCLUDED = "left out with its reason in `pipeline/ui_exclusions.txt`"
# The kinds of reason an interface line is left English for (pipeline/ui_exclusions.txt), each a label and the
# pattern that recognises it; the first match wins, and a reason no pattern matches is reported, never dropped
# (tests/python/test_coverage.py). A reason checked against the client cites the Forever file, table or
# disposition that proves the line never shows, or names what shows it instead.
UI_REASON_CATEGORIES: list[tuple[str, str]] = [
    ("Not on Forever (a retail-era system, a gated addon, an empty client table)",
     r"not on Forever|not displayed on Forever|not displayed in game|^(permanent: )?not displayed"
     r"|retail-era|retail feature|retail-only|not reachable on Forever|unreachable"
     r"|not loaded on camelot|camelot (hides|omits|never|does not|excludes)|the TOC excludes"
     r"|never shows|never opens|never appears|never reached|never built|never fires|never runs"
     r"|never called|which camelot does not load"
     r"|gated off camelot|gated `standard`|no-content|forever_addon_dispositions|AllowLoadGameType|\d rows on"
     r"|absent from the|not in SpellName|has no .* on Forever|Forever (has|carries) no"
     r"|Vanilla (has|recipes have|content|quest templates) (do not show|no)|the Forever tables carry no"
     r"|IsSystemEnabled\(\)|SocialUIFrame|FriendRequestsListSocialViewTemplate|stubbed out|WoW Labs"
     r"|Plunderstorm|Dragonflight|Shadowlands|Legion|Battle for Azeroth|BfA|Burning Crusade|Wrath|Mists"
     r"|Cataclysm|War Within"
     r"|Timerunning|Companion app|mobile-app|Warband|account-wide"
     r"|\(in-game check\)|\[in-game check\]|\[likely\]"
     r"|boosted character|assisted-combat rotation tooltip \(retail\)"),
    ("Spoken by screen narration or text-to-speech, never drawn",
     r"spoken|screen narration|SpeakText|narrat"),
    ("A slash command word or its argument",
     r"command word|slash command|/community argument|a chat command"),
    ("Shown through another key with the same English",
     r"^same English as|its English is also|^one English|shares its English|the same English|an alias of"
     r"|a duplicate of"),
    ("A link label, or a line that is only a link",
     r"no words outside the link|link label|^a link \(|link url|a \|H[a-z]* link|only a link"
     r"|the label of an? \|H"),
    ("No words of its own (markup, numbers, punctuation, an abbreviation)",
     r"no words|no translatable|a number-only|nothing in the ui|format piece|an unnamed label|no text"
     r"|only format specifiers|a constant|glyph|numbers only|only a number|only numbers|no use site"
     r"|nothing to translate|no word to translate|abbreviation|quotes around|indentation|a number and"
     r"|only punctuation|punctuation only|a clock value|^a texture|^an icon|^a colour|^a bare"
     r"|description-run prefix|never a whole line|a prefix|a suffix|a joiner|a separator|placeholder"),
    ("A name, or text the player types or edits",
     r"^(permanent: )?(a name|the name|a player|the word the player|typed|a chat tag|a raid-target tag"
     r"|a community role name|a battle\.net region label)|name slot|name-carrying|name policy"
     r"|names stay English"
     r"|the player (types|typed|edits|names|writes|wrote)|edited by the player|player-edited|player-written"
     r"|player text|player's name|\ba name\b|only the name|the client reads back"),
    ("No Forever file writes it (a C-side line of other content)",
     r"^no Forever UI file writes it|verified absent from the Forever UI extract|no loaded file names it"),
    ("A chat, error or system line another surface owns",
     r"^a pass-through wrapper|a wrapper|chat / error / system message|an error / chat message"
     r"|system message line|chat line|owned by the .* surface|\(UI/[A-Z][A-Za-z]+\)|is the .* surface's"
     r"|another surface|not an item / spell tooltip line"),
    ("Regex noise: a string no screen shows",
     r"regex noise|not read by any|never read|a search tag|a search term|never displayed|only compared"
     r"|developer|debug|not player-facing|not display text|fallback for"),
    ("A composite line no form renders", r"^(permanent|follow-up): "),
    ("A glossary decision: the English word is the Italian one", r"glossary"),
    ("Decided per key: the reason names the client file", r"\.(lua|xml|toc):\d+"),
]
_UI_CATEGORIES = [(label, re.compile(pattern, re.I)) for label, pattern in UI_REASON_CATEGORIES]


def ui_exclusions_by_reason(repo: Path) -> tuple[dict[str, int], list[str]]:
    """→ ({category label: lines}, [keys whose reason fits no category]) over pipeline/ui_exclusions.txt, the
    categories in UI_REASON_CATEGORIES order."""
    counts: dict[str, int] = {label: 0 for label, _ in UI_REASON_CATEGORIES}
    uncategorized: list[str] = []
    path = repo / "pipeline" / "ui_exclusions.txt"
    if not path.is_file():
        return counts, uncategorized
    for raw in path.read_text(encoding="utf-8").splitlines():
        key, sep, reason = raw.partition("#")
        key, reason = key.strip(), reason.strip()
        if not key or not sep:
            continue
        for label, pattern in _UI_CATEGORIES:
            if pattern.search(reason):
                counts[label] += 1
                break
        else:
            uncategorized.append(key)
    return counts, uncategorized
UI_FAMILY_LEFT_OUT = "a client-table row its family's key list leaves out (a name or developer row, ADR-042)"


def _ui_lists(repo: Path) -> tuple[set[str], set[str]]:
    """(the keys `pipeline/ui_keys.txt` ships, the keys `pipeline/ui_exclusions.txt` leaves out)."""
    def keys(name: str) -> set[str]:
        path = repo / "pipeline" / name
        if not path.is_file():
            return set()
        lines = path.read_text(encoding="utf-8").splitlines()
        return {k for raw in lines if (k := raw.split("#", 1)[0].strip())}

    return keys("ui_keys.txt"), keys("ui_exclusions.txt")


def ui_left_out(key: str, ui_keys: set[str], ui_excluded: set[str]) -> str | None:
    """Why an interface line with English and no Italian is not a gap, or None: the key is excluded with a
    reason, or it is a client-table row (`Family:<id>`) the family's curated key list does not ship."""
    if key in ui_excluded:
        return UI_EXCLUDED
    if ":" in key and key not in ui_keys:
        return UI_FAMILY_LEFT_OUT
    return None


def _why(line: dict[str, Any] | None) -> str:
    if line is None:
        return "no Italian yet"
    reasons = line.get("reasons") or []
    return f"{line['status']}: {reasons[0]}" if reasons else line["status"]


def measure(root: Path) -> dict[str, Any]:
    """→ {"types": {type: {...}}, …} over the store at `root` (the repo's data/)."""
    repo = root.parent
    store, english = Store(root), Store(root, english=True)
    types: dict[str, Any] = {}
    ui_keys, ui_excluded = _ui_lists(repo)
    # tooltip lines a batch can never take (a code drafting cannot place): their reason, stated
    blocked: dict[tuple[str, Any, str], str] = {}
    tooltip_kinds = (("item_description", "item"), ("spell_description", "spell"), ("spell_aura", "spell"))
    for kind, type_ in tooltip_kinds:
        for (id_, field), reason in undraftable(root, kind).items():
            blocked[(type_, id_, field)] = reason
    for type_, fields in SURFACE_FIELDS.items():
        en = [ln for ln in english.load(type_) if ln["field"] in fields]
        names = set(objective_names(repo, NAMES_LISTS[type_])) if type_ in NAMES_LISTS else set()
        it = {(ln["id"], ln["field"]): ln for ln in store.load(type_)}
        titles = ({ln["id"]: ln["en"] for ln in english.load("quest") if ln["field"] == "title"}
                  if type_ == "quest" else {})
        done = named = uncounted = 0
        nothing: Counter[str] = Counter()
        missing: Counter[str] = Counter()
        for ln in en:
            j = it.get((ln["id"], ln["field"]))
            if j is not None and shipped(j):
                done += 1
            elif ln["id"] in names:
                named += 1
            elif why := (
                nothing_to_translate(type_, ln["en"], titles.get(ln["id"]), ln["field"])
                or (type_ == "ui" and ui_left_out(str(ln["id"]), ui_keys, ui_excluded))
            ):
                nothing[why] += 1
            else:
                src = str(ln.get("src", "")).split("@")[0]
                wait = ""
                if type_ in ("item", "spell") and src == "wago":
                    wait = (": no text from the Forever tables on this build yet"
                            " (English still from Classic Era); rechecked at each re-pull")
                block = blocked.get((type_, ln["id"], ln["field"])) if j is None else None
                if block:
                    wait = f": the template {template_reason(block)}"
                missing[_why(j) + wait] += 1
                if not wait and (j is None or not j.get("reasons")):
                    uncounted += 1
        kept = sum(
            1 for j in it.values()
            if shipped(j) and isinstance(j.get("ruling"), dict) and j["ruling"].get("ruling") == "accept"
        )
        types[type_] = {"english": len(en), "shipped": done, "names": named + sum(nothing.values()),
                        "kept_english": kept, "missing": dict(missing.most_common()), "uncounted": uncounted,
                        "nothing": dict(nothing.most_common())}
    by_reason, uncategorized = ui_exclusions_by_reason(repo)
    return {"types": types, "quests": quest_states(root), "served": served(repo),
            "ui_left_english": {"by_reason": by_reason, "uncategorized": uncategorized}}


QUEST_LEVELS = "pipeline/quest_levels.tsv"
NO_LEVEL = "assente"
QUEST_STATES = (
    ("translated", "Translated"), ("partial", "Partly translated"), ("untranslated", "Not translated"),
)


def quest_states(root: Path) -> dict[str, Any]:
    """Quests by how much of them ships Italian, over the fields they have English for (a field with nothing
    to translate, or kept English on purpose in pipeline/keep_english.tsv, counts as done): {"no_level":
    {state: [ids]} for the quests `pipeline/quest_levels.tsv` gives no level (`fonte` `assente`), "partial":
    [ids] of every quest with some fields in Italian and others still English}."""
    repo = root.parent
    store, english = Store(root), Store(root, english=True)
    it = {(ln["id"], ln["field"]): ln for ln in store.load("quest")}
    kept = {(i, f): h for (t, i, f), h in read_kept(repo).items() if t == "quest"}
    lines = [ln for ln in english.load("quest") if ln["field"] in SURFACE_FIELDS["quest"]]
    titles = {ln["id"]: ln["en"] for ln in lines if ln["field"] == "title"}
    fields: dict[int, list[bool]] = {}  # quest id → per field to translate: whether its Italian ships
    for ln in lines:
        key = (ln["id"], ln["field"])
        title = titles.get(ln["id"])
        if kept.get(key) == ln["hash"] or nothing_to_translate("quest", ln["en"], title, ln["field"]):
            continue
        j = it.get(key)
        fields.setdefault(ln["id"], []).append(j is not None and shipped(j))

    def state(id_: int) -> str:
        done = fields.get(id_, [])
        if done and all(done) or id_ not in fields and any(k[0] == id_ for k in kept):
            return "translated"
        return "partial" if any(done) else "untranslated"

    no_level: dict[str, list[int]] = {s: [] for s, _ in QUEST_STATES}
    path = repo / QUEST_LEVELS
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines()[1:]:
            parts = raw.split("\t")
            if len(parts) == 4 and parts[3] == NO_LEVEL:
                no_level[state(int(parts[0]))].append(int(parts[0]))
    return {"no_level": {s: sorted(ids) for s, ids in no_level.items()},
            "partial": sorted(i for i in fields if state(i) == "partial")}


def ranges(ids: Sequence[int]) -> str:
    """`1-3, 5, 7`: sorted ids, runs of consecutive ones as a range; "none" for none."""
    runs: list[list[int]] = []
    for i in sorted(set(ids)):
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs) or "none"


def _render_quests(q: dict[str, Any]) -> list[str]:
    if not q:
        return []
    out = ["", "### Quests without a level", "",
           f"The quests `{QUEST_LEVELS}` gives no level (`fonte` `{NO_LEVEL}`: no source knows it), by how",
           "much of them ships Italian.", "", "| Quests | Count | Ids |", "|---|---|---|"]
    out += [f"| {label} | {len(ids):,} | {ranges(ids)} |"
            for s, label in QUEST_STATES for ids in [q["no_level"][s]]]
    out += ["", "### Partly translated quests", "",
            "Quests with some fields in Italian and others still in English (a field kept English on purpose",
            f"or with nothing to translate aside): {len(q['partial']):,}.", "", ranges(q["partial"])]
    return out


def gaps(m: dict[str, Any]) -> dict[str, int]:
    """{type: served lines with neither shipped Italian nor a stated reason}, the types that have any."""
    return {type_: t["uncounted"] for type_, t in m["types"].items() if t["uncounted"]}


def inventory_problems(repo: Path) -> list[str]:
    """Why the served-text inventory does not account for every served column (empty when it does)."""
    columns = read_inventory(repo / "pipeline" / "served_columns.txt")
    dispositions, problems = served_dispositions.parse(repo / "pipeline" / "served_dispositions.txt")
    return problems + served_dispositions.check(columns, dispositions)


def served(repo: Path) -> dict[str, Any]:
    """The served-text inventory by disposition: {"build", "kinds": {kind: [columns, lines]}, "columns":
    [(column, disposition label, lines, evidence)]}; empty when the inventory files are absent."""
    columns_path = repo / "pipeline" / "served_columns.txt"
    dispositions_path = repo / "pipeline" / "served_dispositions.txt"
    if not columns_path.is_file() or not dispositions_path.is_file():
        return {}
    columns = read_inventory(columns_path)
    dispositions, _problems = served_dispositions.parse(dispositions_path)
    kinds: dict[str, list[int]] = {}
    rows = []
    for column, counts in sorted(columns.items()):
        d = dispositions.get(column)
        label = d.label if d else "none"
        lines = served_dispositions.text_lines(counts)
        k = kinds.setdefault(d.kind if d else "none", [0, 0])
        k[0] += 1
        k[1] += lines
        rows.append((column, label, lines, d.evidence if d else ""))
    return {"build": inventory_build(columns_path), "kinds": kinds, "columns": rows}


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "-"


def render(m: dict[str, Any], stamp: str) -> str:
    out = [
        "# Coverage: how much of the game ships in Italian",
        "",
        f"> **Generated** by `make coverage` (`pipeline/wfj/dev/coverage.py`) on {stamp}.",
        "> Do not edit by hand: every pull request that changes `data/` re-runs it. Measured from",
        "> the English the Forever client serves, every line of it; a line that is only a",
        "> name, a placeholder quest or a picture-only page counts as done (nothing to translate).",
        "",
        "## Translation",
        "",
        "| Surface | English lines | Ship Italian | Nothing to translate | Done | Not yet |",
        "|---|---|---|---|---|---|",
    ]
    total_en = total_done = 0
    for type_, t in m["types"].items():
        done = t["shipped"] + t["names"]
        total_en += t["english"]
        total_done += done
        out.append(f"| {LABELS[type_]} | {t['english']:,} | {t['shipped']:,} | {t['names']:,} | "
                   f"{_pct(done, t['english'])} | {t['english'] - done:,} |")
    out.append(f"| **All** | **{total_en:,}** | | | **{_pct(total_done, total_en)}** | "
               f"**{total_en - total_done:,}** |")
    out += ["",
            "Lines shipped as their English under a maintainer ruling (`ruling: accept`, for names, classes,",
            "professions, internal strings): " + (", ".join(
                f"{type_} {t['kept_english']:,}"
                for type_, t in m["types"].items() if t["kept_english"]) or "none") + ".",
            "", "### Nothing to translate (counted as done)", "",
            "| Surface | Why | Lines |", "|---|---|---|"]
    out += [f"| {LABELS[t]} | name only (`{NAMES_LISTS[t]}`) | "
            f"{m['types'][t]['names'] - sum(m['types'][t]['nothing'].values()):,} |"
            for t in NAMES_LISTS if m["types"][t]["names"]]
    out += [f"| {LABELS[type_]} | {why} | {n:,} |" for type_, t in m["types"].items()
            for why, n in t["nothing"].items()]
    out += ["", "### What is not done yet", ""]
    rows = [(type_, why, n) for type_, t in m["types"].items() for why, n in t["missing"].items()]
    if rows:
        out += ["| Surface | Why | Lines |", "|---|---|---|"]
        out += [f"| {LABELS[type_]} | {why} | {n:,} |" for type_, why, n in rows]
    else:
        out.append("Nothing.")
    out += _render_quests(m.get("quests") or {})
    out += _render_ui_left_english(m.get("ui_left_english") or {})
    out += _render_served(m.get("served") or {})
    out.append("")
    return "\n".join(out)


def _render_ui_left_english(u: dict[str, Any]) -> list[str]:
    if not u:
        return []
    out = ["", "### Interface lines left English, by reason", "",
           "Every interface line in `pipeline/ui_exclusions.txt`, by the kind of reason it carries.",
           "A reason that fits no category fails a test instead of dropping out of the count. The reasons",
           "checked against the Forever client cite the file, table or disposition that proves the line",
           "never shows, or the key that already shows the same English.", "",
           "| Reason | Lines |", "|---|---|"]
    out += [f"| {label} | {n:,} |" for label, n in u["by_reason"].items() if n]
    out.append(f"| **All** | **{sum(u['by_reason'].values()):,}** |")
    if u.get("uncategorized"):
        out.append(f"| (no category: {', '.join(u['uncategorized'][:10])}) | {len(u['uncategorized']):,} |")
    return out


KIND_LABELS = {
    "surface": "Shipped through a surface above",
    "names": "Names (stay English)",
    "internal": "Internal (never printed)",
    "no-display": "No place in the Forever client",
    "covered-by": "Same text as another column",
    "empty": "Empty on this build",
    "none": "No disposition yet",
}


def _render_served(sv: dict[str, Any]) -> list[str]:
    if not sv:
        return []
    out = ["", "## Served text inventory", "",
           f"Every text column the client serves on {sv['build']} (`pipeline/served_columns.txt`: its",
           "tables, hotfixes and server caches), with the disposition",
           "`pipeline/served_dispositions.txt` gives it.",
           "Lines are non-empty values; a server cache counts the records this install holds.", "",
           "| Disposition | Columns | Lines |", "|---|---|---|"]
    for kind, label in KIND_LABELS.items():
        if kind in sv["kinds"]:
            cols, lines = sv["kinds"][kind]
            out.append(f"| {label} | {cols:,} | {lines:,} |")
    out += ["", "### Every column", "", "| Column | Disposition | Lines | Why |", "|---|---|---|---|"]
    for column, label, lines, evidence in sv["columns"]:
        why = evidence.replace("|", "/")
        out.append(f"| `{column}` | {label} | {lines:,} | {why} |")
    return out


def _stamp(repo: Path) -> str:
    try:
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    return f"{date.today().isoformat()} at commit `{sha}`"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wfj.dev.coverage", description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", type=Path, help="write the markdown here (default: print it)")
    ap.add_argument("--build", help="the pinned Forever build: refuse an inventory taken on another")
    a = ap.parse_args(argv)
    root = data_root()
    taken = inventory_build(root.parent / "pipeline" / "served_columns.txt")
    if a.build and taken != a.build:
        print(f"coverage: pipeline/served_columns.txt is from {taken}, the pinned build is {a.build}: "
              "run `make served-columns` and give each new column a disposition")
        return 1
    problems = inventory_problems(root.parent)
    if problems:
        print("coverage: the served-text inventory has columns without a stated disposition:")
        for p in problems:
            print(f"  {p}")
        return 1
    text = render(measure(root), _stamp(root.parent))
    if a.out:
        a.out.write_text(text, encoding="utf-8")
        print(f"coverage: wrote {a.out}")
        for rel in readme_counts.write(root.parent):
            print(f"coverage: updated the counts in {rel}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
