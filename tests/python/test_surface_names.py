from wfj.dev.surface_names import collect, lua_file, lua_string


def test_a_name_goes_to_its_own_kind():
    out = collect([("oggetto", "Claw", "Artiglio"), ("abilita", "Claw", "Unghiata")])
    assert out["oggetto"]["Claw"] == "Artiglio"
    assert out["abilita"]["Claw"] == "Unghiata"


def test_the_most_common_italian_wins_and_a_tie_ships_nothing():
    rows = [("zona", "A", "Uno"), ("zona", "A", "Uno"), ("zona", "A", "Due"), ("zona", "B", "X"), ("zona", "B", "Y")]
    assert collect(rows) == {"zona": {"A": "Uno"}}


def test_internal_rows_and_unchanged_names_are_left_out():
    rows = [("oggetto", "[PH] Sword", "Spada"), ("oggetto", "Monster - Axe", "Ascia"), ("oggetto", "Dalaran", "Dalaran"),
            ("fazione", "PLAYER, Human", "GIOCATORE, Umano"), ("creatura", "Hogger", "Porcone")]
    assert collect(rows) == {}


def test_the_addon_file_holds_no_english():
    text = lua_file("nameitem", {"Worn Shortsword": 'Spada "Corta"'})
    assert "Worn" not in text
    assert 'WFJ.Data.add("nameitem"' in text
    assert lua_string('Spada "Corta"') in text


def test_coined_names_are_objects_spells_and_zones_only(tmp_path):
    """`pipeline/nomi_coniati.tsv`: the project's names for what Forever added (no Italian client has them)."""
    import pytest

    from wfj.dev.surface_names import coined_rows

    good = tmp_path / "ok.tsv"
    good.write_text("tipo\ten\tit\tnota\noggetto\tCamp Tent\tTenda da Campo\t\n"
                    "abilita\tBasic Campfire\tFuoco da Campo Semplice\tcampeggio\n"
                    "zona\tBandarion Keep\tForte Bandarion\tForever\n", encoding="utf-8")
    assert list(coined_rows(good)) == [("oggetto", "Camp Tent", "Tenda da Campo"),
                                       ("abilita", "Basic Campfire", "Fuoco da Campo Semplice"),
                                       ("zona", "Bandarion Keep", "Forte Bandarion")]
    for bad in ("fazione\tElwynn\tElwynn\t\n", "oggetto\tCamp Tent\t\t\n"):
        path = tmp_path / "bad.tsv"
        path.write_text("tipo\ten\tit\tnota\n" + bad, encoding="utf-8")
        with pytest.raises(ValueError):
            list(coined_rows(path))


def test_the_shipped_coined_names_load():
    from wfj.dev.surface_names import coined_rows

    rows = list(coined_rows())
    assert ("abilita", "Basic Campfire", "Fuoco da Campo Semplice") in rows
    assert len({en for _, en, _ in rows}) == len(rows)  # one Italian per English
