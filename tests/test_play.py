import pytest

from dartagnan.display.buttons import Action
from dartagnan.display.screens.play import dart_for
from dartagnan.game.darts import BULL, MISS, Dart


@pytest.mark.parametrize(
    ("key", "action", "expected"),
    [
        ("20", Action.SINGLE, Dart(20, 1)),
        ("20", Action.DOUBLE, Dart(20, 2)),
        ("20", Action.TRIPLE, Dart(20, 3)),
        ("25", Action.SINGLE, Dart(BULL, 1)),
        ("25", Action.DOUBLE, Dart(BULL, 2)),
        ("Bull", Action.SINGLE, Dart(BULL, 2)),
        ("Bull", Action.TRIPLE, Dart(BULL, 2)),
        ("Raté", Action.DOUBLE, Dart(MISS, 1)),
    ],
)
def test_touche_et_geste_donnent_la_flechette(key, action, expected):
    assert dart_for(key, action) == expected


def test_triple_25_refuse():
    assert dart_for("25", Action.TRIPLE) == "Le triple 25 n'existe pas"
