from wfj.core.language import is_italian


def test_is_italian():
    assert is_italian("Uccidi 10 lupi nella Foresta di Elwynn.")
    assert is_italian("Città")
    assert not is_italian("")
    assert not is_italian("Kill 10 wolves.", english="Kill 10 wolves.")  # identico all'inglese
    assert not is_italian("狼を10匹倒せ")  # nessuna lettera latina


def test_is_italian_edges():
    assert not is_italian("   ")
    assert not is_italian("10 / 20 …")  # solo cifre e punteggiatura
    assert is_italian("È")  # una lettera accentata basta
    assert not is_italian("Kill  10 wolves. ", english="Kill 10 wolves.")  # uguale dopo normalize_v1
    assert is_italian("Uccidi 10 lupi.", english="Kill 10 wolves.")
