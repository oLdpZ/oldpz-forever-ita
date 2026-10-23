"""Nomi ufficiali dei PNG: Creature.db2 (wago) e Wowhead, solo dove l'inglese e' quello di Forever."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wfj.dev import creature_official as co

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "wowhead"
HEAD = "ID,Name_lang,NameAlt_lang,Title_lang,TitleAlt_lang\n"

ENGLISH = {
    (3, "name"): "Flesh Eater",
    (4, "name"): "Defias Thug",
    (4, "subname"): "Weapon Merchant",
    (5, "name"): "Gibbert",
    (12696, "name"): "Senani Thunderheart",
}


def _csvs(tmp_path: Path) -> tuple[Path, Path]:
    en = tmp_path / "Creature.enUS.csv"
    it = tmp_path / "Creature.itIT.csv"
    en.write_text(
        HEAD + '3,Flesh Eater,,,\n4,Defias Thug,,"Weapon Merchant",\n5,Gibbert Retail,,,\n', encoding="utf-8"
    )
    it.write_text(
        HEAD + '3,Mangiatore di Carne,,,\n4,Furfante Defias,,"Mercante di armi",\n5,Gibberto,,,\n',
        encoding="utf-8",
    )
    return en, it


def test_db2_kept_only_when_english_matches(tmp_path: Path) -> None:
    en, it = _csvs(tmp_path)
    got = co.from_db2(en, it, ENGLISH)
    assert (3, "name", "Flesh Eater", "Mangiatore di Carne", "db2") in got
    assert (4, "name", "Defias Thug", "Furfante Defias", "db2") in got
    assert (4, "subname", "Weapon Merchant", "Mercante di armi", "db2") in got
    assert all(o[0] != 5 for o in got)  # inglese retail diverso da quello di Forever


def _fixture_fetch(id_: int, locale: int) -> dict | None:
    if id_ == 12696:
        return json.loads((FIX / f"npc-12696-{locale}.json").read_text(encoding="utf-8"))
    return None


def test_wowhead_uses_name_and_checks_english() -> None:
    got = co.from_wowhead([12696, 5], _fixture_fetch, ENGLISH)
    assert got == [(12696, "name", "Senani Thunderheart", "Senani Cuore Tonante", "wowhead")]
    other = {(12696, "name"): "Something Else"}
    assert co.from_wowhead([12696], _fixture_fetch, other) == []


def test_wowhead_bracketed_name_is_untranslated() -> None:
    def fetch(id_: int, locale: int) -> dict | None:
        return {"name": "Waypoint" if locale == 0 else "[Waypoint]"}

    assert co.from_wowhead([1], fetch, {(1, "name"): "Waypoint"}) == []


def test_db2_wins_over_wowhead(tmp_path: Path) -> None:
    en, it = _csvs(tmp_path)
    asked: list[int] = []

    def fetch(id_: int, locale: int) -> dict | None:
        asked.append(id_)
        return {"name": "Senani Thunderheart" if locale == 0 else "Altro"}

    rows = co.build(en, it, ENGLISH, fetch)
    assert 3 not in asked and 4 not in asked  # db2 ha gia' il nome: Wowhead non si interroga
    assert 5 in asked and 12696 in asked
    assert [r for r in rows if r[0] == 3] == [(3, "name", "Flesh Eater", "Mangiatore di Carne", "db2")]
    assert rows == sorted(rows, key=lambda r: (r[0], r[1]))


def test_fetch_cached_reads_cache_and_waits(tmp_path: Path) -> None:
    calls: list[str] = []
    slept: list[float] = []
    now = [100.0]

    def get(url: str) -> str | None:
        calls.append(url)
        return '{"name": "Hogger"}' if "/448?" in url else '{"error": "not found"}'

    def sleep(s: float) -> None:
        slept.append(s)
        now[0] += s

    kw = {"get": get, "sleep": sleep, "clock": lambda: now[0]}
    assert co.fetch_cached(448, 0, tmp_path, **kw) == {"name": "Hogger"}
    assert co.fetch_cached(448, 0, tmp_path, **kw) == {"name": "Hogger"}
    assert len(calls) == 1 and "locale=0" in calls[0] and "dataEnv=1" in calls[0]
    assert co.fetch_cached(9, 9, tmp_path, **kw) is None  # non esiste: None...
    assert co.fetch_cached(9, 9, tmp_path, **kw) is None  # ...e registrato, non richiesto di nuovo
    assert len(calls) == 2
    assert slept and slept[-1] >= 1.0  # almeno un secondo tra due richieste vere
    assert (tmp_path / "448.0.json").is_file() and (tmp_path / "9.9.json").read_text() == ""


def test_fetch_cached_retries_then_gives_up(tmp_path: Path) -> None:
    n = [0]

    def get(url: str) -> str | None:
        n[0] += 1
        if n[0] < 3:
            raise co.Transient("HTTP 429")
        return '{"name": "X"}'

    got = co.fetch_cached(7, 0, tmp_path, get=get, sleep=lambda s: None, clock=lambda: 0.0)
    assert got == {"name": "X"} and n[0] == 3


def test_wowhead_italian_equal_to_english_or_placeholder_is_dropped() -> None:
    names = {
        1: ("Thrall", "Thrall"),
        2: ("[UNUSED] Marlon Darnik", "[UNUSED] Marlon Darnik"),
        3: ("Hogger", "Boccalarga"),
    }
    english = {(i, "name"): en for i, (en, _) in names.items()}

    def fetch(id_: int, locale: int) -> dict | None:
        return {"name": names[id_][0 if locale == 0 else 1]}

    assert co.from_wowhead([1, 2, 3], fetch, english) == [(3, "name", "Hogger", "Boccalarga", "wowhead")]


def test_only_a_clear_miss_is_cached(tmp_path: Path) -> None:
    kw = {"sleep": lambda s: None, "clock": lambda: 0.0}
    assert co.fetch_cached(1, 0, tmp_path, get=lambda u: None, **kw) is None  # 404
    assert (tmp_path / "1.0.json").read_text() == ""
    assert co.fetch_cached(2, 0, tmp_path, get=lambda u: "{}", **kw) is None
    assert (tmp_path / "2.0.json").is_file()
    for n, body in enumerate(["<html>blocked</html>", '{"name": "Tru', '{"foo": 1}', "[1]"], start=10):

        def bad(u: str, body: str = body) -> str:
            return body

        with pytest.raises(co.Transient):
            co.fetch_cached(n, 0, tmp_path, get=bad, **kw)
        assert not (tmp_path / f"{n}.0.json").exists()


def test_http_other_4xx_is_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    import urllib.error

    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b""))

    monkeypatch.setattr(co.urllib.request, "urlopen", boom)
    with pytest.raises(co.Transient):
        co._http_get("https://example.invalid/x")


def test_guarded_aborts_after_consecutive_failures() -> None:
    def down(id_: int, locale: int) -> dict | None:
        raise co.Transient("HTTP 503")

    g = co.guarded(down, limit=3)
    assert g(1, 0) is None and g(1, 9) is None and g(2, 0) is None  # two ids so far
    with pytest.raises(co.Aborted):
        g(3, 0)

    ok = [False]

    def flaky(id_: int, locale: int) -> dict | None:
        if ok[0]:
            return {"name": "X"}
        raise co.Transient("x")

    h = co.guarded(flaky, limit=3)
    h(1, 0), h(2, 0)
    ok[0] = True
    assert h(3, 0) == {"name": "X"}
    ok[0] = False
    h(4, 0), h(5, 0)  # the success reset the count
