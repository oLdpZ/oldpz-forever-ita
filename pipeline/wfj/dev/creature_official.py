"""Official Italian NPC names: `pipeline/creature_official.tsv` (id, field, en, it, fonte).

    python -m wfj.dev.creature_official --retail <retail dir> --build <build> [--cache <dir>] [--no-wowhead]

Two Blizzard sources, each kept only where its English is the English Forever shows (data/english/unit):
`db2` is Creature.db2 from wago.tools (`Name_lang` -> name, `Title_lang` -> subname, enUS and itIT), `wowhead`
is the Wowhead tooltip endpoint (the `name` of locale 0 and locale 9; the title is not asked there, its
`tooltip` field is not reliable for it). db2 wins; Wowhead is asked only for the ids db2 gave no name for.
Wowhead answers are cached one file per (id, locale), a miss as an empty file, so a rerun resumes."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from wfj.io import retail, tables_stamp
from wfj.io.jsonl_store import Store
from wfj.paths import data_root

Official = tuple[int, str, str, str, str]
OUT = Path(__file__).resolve().parents[2] / "creature_official.tsv"
HEADER = "id\tfield\ten\tit\tfonte"
CACHE = Path("/root/inputs/wowhead-npc")
URL = "https://nether.wowhead.com/tooltip/npc/{id}?dataEnv=1&locale={locale}"
AGENT = "OldpZ_ForeverITA-pipeline/1.0 (personal translation addon)"
COLUMNS = (("name", "Name_lang"), ("subname", "Title_lang"))
RETRIES = 5
MAX_FAILED_IN_A_ROW = 20

_last_request = [float("-inf")]


class Transient(Exception):
    """A response worth retrying later (HTTP 429, 5xx, a dropped connection)."""


def _column(path: Path, col: str) -> dict[int, str]:
    out: dict[int, str] = {}
    with Path(path).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "ID" not in reader.fieldnames or col not in reader.fieldnames:
            raise ValueError(f"{Path(path).name}: need columns ID and {col}")
        for row in reader:
            text = (row[col] or "").strip()
            if text:
                out[int(row["ID"])] = text
    return out


def from_db2(en_csv: Path, it_csv: Path, english: dict[tuple[int, str], str]) -> list[Official]:
    out: list[Official] = []
    for field, col in COLUMNS:
        en, it = _column(en_csv, col), _column(it_csv, col)
        for id_, text in sorted(en.items()):
            forever = english.get((id_, field))
            if forever is not None and text == forever.strip() and id_ in it:
                out.append((id_, field, forever, it[id_], "db2"))
    return out


def _name(doc: dict[str, Any] | None) -> str:
    return str(doc.get("name") or "").strip() if isinstance(doc, dict) else ""


def from_wowhead(
    ids: Iterable[int],
    fetch: Callable[[int, int], dict[str, Any] | None],
    english: dict[tuple[int, str], str],
) -> list[Official]:
    out: list[Official] = []
    for id_ in ids:
        forever = english.get((id_, "name"))
        if forever is None:
            continue
        en = _name(fetch(id_, 0))
        if en != forever.strip() or en.startswith("["):  # "[UNUSED] ...", "[DND] ..."
            continue
        it = _name(fetch(id_, 9))
        # Wowhead wraps a name it has no Italian for in brackets ("[Waypoint]"); an Italian equal to the
        # English is no evidence of a Blizzard translation: those names go to the lots
        if it and not it.startswith("[") and it != en:
            out.append((id_, "name", forever, it, "wowhead"))
    return out


def _http_get(url: str) -> str | None:
    """The body of a 200; None for HTTP 404 (no such NPC); Transient for anything else."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise Transient(f"HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise Transient(str(e)) from None


def _parse(text: str) -> dict[str, Any] | None:
    """The tooltip document of a cache file or a response; None for a recorded miss (empty text)."""
    try:
        doc = json.loads(text) if text.strip() else None
    except ValueError:
        return None
    return doc if isinstance(doc, dict) and _name(doc) else None


def _answer(text: str | None) -> dict[str, Any] | None:
    """A response body as a tooltip document, or None for a clear miss (404, `{}`, `{"error": ...}`);
    anything else (HTML, truncated JSON, an unknown shape) is Transient and not cached."""
    if text is None:
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        raise Transient("not JSON") from None
    if not isinstance(doc, dict):
        raise Transient("unexpected JSON")
    if _name(doc):
        return doc
    if not doc or "error" in doc:
        return None
    raise Transient("JSON without a name")


def fetch_cached(
    id_: int,
    locale: int,
    cache_dir: Path,
    min_interval: float = 1.0,
    *,
    get: Callable[[str], str | None] = _http_get,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any] | None:
    """The Wowhead tooltip JSON of an NPC, or None where there is no such NPC. Cached on disk (a miss is an
    empty file); real requests are `min_interval` seconds apart, and a 429/5xx backs off and retries."""
    path = Path(cache_dir) / f"{id_}.{locale}.json"
    if path.is_file():
        return _parse(path.read_text(encoding="utf-8"))
    delay = 5.0
    doc: dict[str, Any] | None = None
    for attempt in range(RETRIES):
        wait = _last_request[0] + min_interval - clock()
        if wait > 0:
            sleep(wait)
        _last_request[0] = clock()
        try:
            doc = _answer(get(URL.format(id=id_, locale=locale)))
            break
        except Transient:
            if attempt == RETRIES - 1:
                raise
            sleep(delay)
            delay *= 3
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps(doc, ensure_ascii=False) if doc else "", encoding="utf-8")
    tmp.replace(path)
    return doc


class Aborted(Exception):
    """Too many ids in a row could not be fetched: Wowhead is down or blocking us."""


def guarded(
    fetch: Callable[[int, int], dict[str, Any] | None], limit: int = MAX_FAILED_IN_A_ROW
) -> Callable[[int, int], dict[str, Any] | None]:
    """`fetch` where a Transient failure reads as no answer for that id, and `limit` ids in a row failing
    raises Aborted."""
    run = [0]
    last: list[int | None] = [None]

    def call(id_: int, locale: int) -> dict[str, Any] | None:
        try:
            doc = fetch(id_, locale)
        except Transient:
            if last[0] != id_:
                run[0] += 1
                last[0] = id_
            if run[0] >= limit:
                raise Aborted(f"{run[0]} ids in a row failed") from None
            return None
        run[0] = 0
        return doc

    return call


def build(
    en_csv: Path,
    it_csv: Path,
    english: dict[tuple[int, str], str],
    fetch: Callable[[int, int], dict[str, Any] | None] | None,
) -> list[Official]:
    rows = from_db2(en_csv, it_csv, english)
    if fetch is not None:
        have = {r[0] for r in rows if r[1] == "name"}
        ids = sorted({i for i, f in english if f == "name" and i not in have})
        rows += from_wowhead(ids, fetch, english)
    return sorted(rows, key=lambda r: (r[0], r[1]))


def write_tsv(path: Path, rows: Iterable[Official]) -> None:
    body = "".join(f"{i}\t{f}\t{en}\t{it}\t{src}\n" for i, f, en, it, src in rows)
    Path(path).write_text(HEADER + "\n" + body, encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj.dev.creature_official", description=__doc__.split("\n", 1)[0])
    p.add_argument("--retail", type=Path, required=True)
    p.add_argument("--build", required=True)
    p.add_argument("--data", type=Path, default=None)
    p.add_argument("--cache", type=Path, default=CACHE)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--no-wowhead", action="store_true", help="db2 only")
    p.add_argument("--only", type=int, nargs="*", help="restrict to these ids (smoke run)")
    a = p.parse_args(argv)
    try:
        tables_stamp.check(retail.files(a.retail, ["Creature"]), "wago", a.build)
        store = Store(a.data or data_root(), english=True)
        english = {(ln["id"], ln["field"]): ln["en"].strip() for ln in store.load("unit")}
    except (OSError, ValueError) as e:
        print(f"creature_official: {e}", file=sys.stderr)
        return 1
    if a.only:
        english = {k: v for k, v in english.items() if k[0] in set(a.only)}
    done = [0]
    failed: list[int] = []

    def fetch(id_: int, locale: int) -> dict[str, Any] | None:
        done[0] += 1
        if done[0] % 200 == 0:
            print(f"creature_official: {done[0]} lookups, id {id_}", flush=True)
        try:
            return fetch_cached(id_, locale, a.cache)
        except Transient as e:
            failed.append(id_)
            print(f"creature_official: id {id_} locale {locale} skipped ({e}); rerun to retry", flush=True)
            raise

    try:
        rows = build(
            retail.csv_path(a.retail, "Creature", "enUS"),
            retail.csv_path(a.retail, "Creature", "itIT"),
            english,
            None if a.no_wowhead else guarded(fetch),
        )
    except Aborted as e:
        print(f"creature_official: aborted, {e}; the cache is kept, rerun to resume", file=sys.stderr)
        return 2
    write_tsv(a.out, rows)
    n = {s: sum(1 for r in rows if r[4] == s) for s in ("db2", "wowhead")}
    print(
        f"creature_official: {len(rows)} rows ({n['db2']} db2, {n['wowhead']} wowhead), {len(failed)} skipped"
    )
    if a.only:
        for r in rows:
            print("\t".join(map(str, r)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
