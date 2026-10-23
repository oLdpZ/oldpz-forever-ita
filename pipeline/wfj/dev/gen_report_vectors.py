"""Generate the shared fix-report vectors: canonical JSONL + a Lua twin for busted.

Usage: python -m wfj.dev.gen_report_vectors <vectors-dir>
`cases`: the pending fixes the addon holds → the report text `Core/ReportText.lua` must write byte for byte
and `core/fix_report.parse` must read back to the same fixes. `bad`: texts the parser refuses, with a piece of
the message. Both files are committed; tests/python/test_fix_report.py fails if a regeneration differs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from wfj.core import fix_report
from wfj.core.hashing import it_hash
from wfj.emit.lua_writer import lua_string

IT1 = "Kobold Verminを10体倒せ。"
IT2 = "旅人よ、よく来た。\n\nこの地は長く闇に包まれている。"
IT3 = "パイプ|記号\\と改行\nを含む行"
NOTE_MAX = "あ" * 66 + "ab"  # 198 + 2 = 200 bytes
IT_MAX = "日" * 2666 + "ab"  # 7998 + 2 = 8000 bytes
# shipped Italian holds carriage returns (a `\r\n` popup line, a `\n\r` book page)
IT_CR = "全部売却しますか？\r\n続行しますか？\n\rStone"


def _fix(type_: str, id_: int | str, field: str, it: str, reason: str, note: str = "", sug: str = "") -> dict:
    d: dict[str, Any] = {"type": type_, "id": id_, "field": field, "it_hash": it_hash(it), "reason": reason}
    if note:
        d["note"] = note
    if sug:
        d["it"] = sug
    return d


CASES: list[tuple[str, str, str, list[dict]]] = [
    ("one-plain", "1.0.0", "1.60.1.70009", [_fix("quest", 783, "objectives", IT1, "wrong")]),
    (
        "note-and-it",
        "1.0.0",
        "1.60.1.70009",
        [
            _fix(
                "quest",
                7,
                "description",
                IT2,
                "awkward",
                note="stiff wording",
                sug="旅の者よ、よく来てくれた。\n\n長い間、この地は闇の中だ。",
            ),
        ],
    ),
    (
        "escapes",
        "1.0.0",
        "1.60.1.70009",
        [
            _fix(
                "gossip", "0001ce030c010973", "text", IT3, "typo", note="a | and a \\ here", sug=IT3 + "|x\\n"
            ),
        ],
    ),
    (
        "keys",
        "0.9.2-beta",
        "1.60.1.69913",
        [
            _fix("ui", "ItemSubClass:2:3", "text", "銃", "name"),
            _fix("ui", "ABANDON_QUEST", "text", "クエスト放棄", "other", note="short"),
            _fix("book", "8f0e2a11b3c4d5e6", "text", "古い手紙", "awkward"),
            _fix("item", 2589, "description", "布の切れ端。", "typo", sug="布の切れ端"),
            _fix("spell", 133, "aura", "炎上中。", "wrong"),
            _fix("objective", 4021, "text", "Drullを救出", "name"),
            _fix("area", 76, "text", "Fargodeep Mineを調査する", "other"),
            _fix("unit", 12696, "name", "セナニ・サンダーハート", "name"),
        ],
    ),
    (
        "max-sizes",
        "1.0.0",
        "1.60.1.70009",
        [
            _fix("quest", 12, "completion", "よくやった。", "awkward", note=NOTE_MAX, sug=IT_MAX),
        ],
    ),
    ("unknown-build", "?", "?", [_fix("quest", 1, "title", "「Chow」クエスト", "other")]),
    (
        "carriage-returns",
        "@project-version@",
        "1.60.1.70009",
        [_fix("ui", "SELL_ALL_JUNK_ITEMS_POPUP", "text", IT_CR, "typo", sug=IT_CR.replace("続行", "続けて"))],
    ),
]

H = it_hash(IT1)
GOOD_HEAD = "OFI-REPORT 1\naddon 1.0.0 client 1.60.1.70009\n"
BAD: list[tuple[str, str, str]] = [
    ("no-header", "hello\nfix quest 1 title " + H + " wrong\nend 1\n", "no report found"),
    ("version", "OFI-REPORT 2\naddon 1 client 2\nend 0\n", "unknown report version"),
    ("no-addon-line", "OFI-REPORT 1\nfix quest 1 title " + H + " wrong\nend 1\n", "expected `addon"),
    ("cut-no-end", GOOD_HEAD + "fix quest 1 title " + H + " wrong\n", "no `end` line"),
    ("cut-count", GOOD_HEAD + "fix quest 1 title " + H + " wrong\nend 2\n", "the paste was cut"),
    ("type", GOOD_HEAD + "fix npc 1 title " + H + " wrong\nend 1\n", "unknown type"),
    ("field", GOOD_HEAD + "fix quest 1 name " + H + " wrong\nend 1\n", "has no field"),
    ("hash", GOOD_HEAD + "fix quest 1 title ABCDEF wrong\nend 1\n", "16 lowercase hex"),
    ("reason", GOOD_HEAD + "fix quest 1 title " + H + " bad\nend 1\n", "unknown reason"),
    ("numeric-id", GOOD_HEAD + "fix quest 012 title " + H + " wrong\nend 1\n", "positive number"),
    ("gossip-id", GOOD_HEAD + "fix gossip 12 text " + H + " wrong\nend 1\n", "16 lowercase hex"),
    ("ui-id", GOOD_HEAD + "fix ui not_a_key text " + H + " wrong\nend 1\n", "not a UI key"),
    ("note-first", GOOD_HEAD + "note hi\nfix quest 1 title " + H + " wrong\nend 1\n", "before any `fix`"),
    (
        "note-twice",
        GOOD_HEAD + "fix quest 1 title " + H + " wrong\nnote a\nnote b\nend 1\n",
        "repeated or out",
    ),
    (
        "note-after-it",
        GOOD_HEAD + "fix quest 1 title " + H + " wrong\nit あ\nnote b\nend 1\n",
        "repeated or out",
    ),
    ("bad-escape", GOOD_HEAD + "fix quest 1 title " + H + " wrong\nit a\\tb\nend 1\n", "bad escape"),
    ("note-newline", GOOD_HEAD + "fix quest 1 title " + H + " wrong\nnote a\\nb\nend 1\n", "one line"),
    (
        "note-long",
        GOOD_HEAD + "fix quest 1 title " + H + " wrong\nnote " + NOTE_MAX + "x\nend 1\n",
        "over 200",
    ),
    ("it-long", GOOD_HEAD + "fix quest 1 title " + H + " wrong\nit " + IT_MAX + "x\nend 1\n", "over 8000"),
    (
        "note-cr",
        GOOD_HEAD + "fix quest 1 title " + H + " wrong\nnote a\\rb\nend 1\n",
        "one line",
    ),
    # the header's tokens are echoed in the issue comment, so nothing in them may render
    (
        "header-markdown",
        "OFI-REPORT 1\naddon ![x](https://e.example/p.png) client @octocat\nend 0\n",
        "expected `addon",
    ),
    ("header-long", "OFI-REPORT 1\naddon " + "1" * 41 + " client 2\nend 0\n", "expected `addon"),
    ("empty-it", GOOD_HEAD + "fix quest 1 title " + H + " wrong\nit \nend 1\n", "an empty `it`"),
    (
        "duplicate",
        GOOD_HEAD + "fix quest 1 title " + H + " wrong\nfix quest 1 title " + H + " typo\nend 2\n",
        "already reported",
    ),
    ("two-reports", GOOD_HEAD + "end 0\n" + GOOD_HEAD + "end 0\n", "a second report"),
    ("stray", GOOD_HEAD + "hello there\nend 0\n", "unexpected line"),
]


def build() -> dict[str, list[dict]]:
    cases = []
    for cid, addon, client, fixes in CASES:
        rep = fix_report.Report(addon=addon, client=client, fixes=[fix_report.Fix(**f) for f in fixes])
        cases.append(
            {"id": cid, "addon": addon, "client": client, "fixes": fixes, "text": fix_report.render(rep)}
        )
    bad = [{"id": bid, "text": text, "error": err} for bid, text, err in BAD]
    return {"cases": cases, "bad": bad}


def _lua_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return lua_string(v)
    if isinstance(v, list):
        return "{ " + ", ".join(_lua_value(x) for x in v) + " }"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_lua_value(x)}" for k, x in v.items()) + " }"
    raise TypeError(type(v))


def to_lua(v: dict[str, list[dict]]) -> str:
    lines = [
        "-- GENERATED by pipeline/wfj/dev/gen_report_vectors.py from report_vectors.jsonl. Do not edit.",
        "return { cases = {",
    ]
    lines += [f"  {_lua_value(c)}," for c in v["cases"]]
    lines.append("}, bad = {")
    lines += [f"  {_lua_value(b)}," for b in v["bad"]]
    lines.append("} }")
    return "\n".join(lines) + "\n"


def write(out_dir: Path) -> None:
    v = build()
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "report_vectors.jsonl").open("w", encoding="utf-8") as f:
        for kind in ("cases", "bad"):
            for row in v[kind]:
                f.write(
                    json.dumps({"kind": kind[:-1] if kind == "cases" else kind, **row}, ensure_ascii=False)
                    + "\n"
                )
    (out_dir / "report_vectors.lua").write_text(to_lua(v), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    out = Path(args[0]) if args else Path(__file__).resolve().parents[3] / "vectors"
    write(out)
    print(f"wrote {out / 'report_vectors.jsonl'} and .lua ({len(CASES)} cases, {len(BAD)} bad)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
