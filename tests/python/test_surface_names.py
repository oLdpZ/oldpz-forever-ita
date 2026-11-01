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
