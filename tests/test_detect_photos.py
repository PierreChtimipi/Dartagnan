import sys
from pathlib import Path

import pytest

from dartagnan.game.darts import BULL, MISS, Dart

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from detect_photos import same_zone


@pytest.mark.parametrize(
    ("truth", "dart", "expected"),
    [
        ("20", Dart(20, 1), True),
        ("T19", Dart(19, 3), True),
        ("t19", Dart(19, 3), True),
        ("D5", Dart(5, 1), False),
        ("25", Dart(BULL, 1), True),
        ("Bull", Dart(BULL, 2), True),
        ("Out", Dart(MISS, 1), True),
        ("Raté", Dart(MISS, 1), True),
        ("Out", Dart(3, 2), False),
        ("20", None, False),
    ],
)
def test_zone_reelle_et_zone_detectee(truth, dart, expected):
    assert same_zone(truth, dart) is expected
