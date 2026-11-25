from dartagnan.display.buttons import (DOUBLE_WINDOW, LONG_PRESS, REPEAT_DELAY, Action, Button,
                                       Buttons)


def test_appui_court_simple_apres_delai():
    b = Buttons()
    b.press(Button.SELECT, 0)
    b.release(Button.SELECT, 0.1)
    assert b.update(0.2) == []
    assert b.update(0.1 + DOUBLE_WINDOW + 0.01) == [Action.SINGLE]
    assert b.update(2) == []


def test_deux_appuis_rapides_double():
    b = Buttons()
    b.press(Button.SELECT, 0)
    b.release(Button.SELECT, 0.1)
    assert b.press(Button.SELECT, 0.25) == [Action.DOUBLE]
    b.release(Button.SELECT, 0.3)
    assert b.update(2) == []


def test_appui_long_triple_une_seule_fois():
    b = Buttons()
    b.press(Button.SELECT, 0)
    assert b.update(LONG_PRESS - 0.01) == []
    assert b.update(LONG_PRESS) == [Action.TRIPLE]
    assert b.update(LONG_PRESS + 1) == []
    b.release(Button.SELECT, 2)
    assert b.update(3) == []


def test_gauche_droite_immediat_et_repete():
    b = Buttons()
    assert b.press(Button.RIGHT, 0) == [Action.RIGHT]
    assert b.update(REPEAT_DELAY - 0.01) == []
    assert b.update(REPEAT_DELAY) == [Action.RIGHT]
    b.release(Button.RIGHT, 1)
    assert b.update(5) == []
