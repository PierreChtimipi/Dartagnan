import math

import numpy as np
import pytest

from dartagnan.game.darts import BULL, MISS, Dart
from dartagnan.geometry.board import (
    CALIBRATION_POINTS,
    DOUBLE_OUTER_RADIUS,
    board_point,
    dart_at,
    sector_boundary,
)
from dartagnan.geometry.calibration import board_to_image, image_to_board, project


def at(angle: float, radius: float) -> Dart:
    return dart_at(*board_point(angle, radius))


@pytest.mark.parametrize(
    ("angle", "sector"), [(0, 20), (90, 6), (180, 3), (270, 11), (18, 1), (342, 5)]
)
def test_secteur_au_centre_de_sa_zone(angle, sector):
    assert at(angle, 50) == Dart(sector, 1)


def test_limite_entre_deux_secteurs():
    assert at(sector_boundary(0) - 0.1, 50).segment == 20
    assert at(sector_boundary(0) + 0.1, 50).segment == 1
    assert at(360 - sector_boundary(0) + 0.1, 50).segment == 20


@pytest.mark.parametrize(
    ("radius", "expected"),
    [
        (0, Dart(BULL, 2)),
        (6.34, Dart(BULL, 2)),
        (6.35, Dart(BULL, 1)),
        (15.89, Dart(BULL, 1)),
        (15.9, Dart(20, 1)),
        (98.9, Dart(20, 1)),
        (99, Dart(20, 3)),
        (106.9, Dart(20, 3)),
        (107, Dart(20, 1)),
        (161.9, Dart(20, 1)),
        (162, Dart(20, 2)),
        (169.9, Dart(20, 2)),
        (170, Dart(MISS, 1)),
        (300, Dart(MISS, 1)),
    ],
)
def test_limites_des_anneaux(radius, expected):
    assert at(0, radius) == expected


def test_points_de_calibration_sur_le_bord_du_double_a_90_degres():
    for i, (x, y) in enumerate(CALIBRATION_POINTS):
        assert math.hypot(x, y) == pytest.approx(DOUBLE_OUTER_RADIUS)
        assert math.degrees(math.atan2(x, y)) % 360 == pytest.approx(9 + 90 * i)


def test_homographie_retrouve_la_cible_depuis_l_image():
    # Caméra simulée : cible vue en perspective, points cliqués exactement
    camera = np.array([[1.2, 0.3, 640], [-0.1, -0.8, 360], [0.0005, 0.001, 1]])
    clicked = [tuple(p) for p in project(camera, list(CALIBRATION_POINTS))]
    homography = board_to_image(clicked)

    bull = project(camera, [(0, 0)])[0]
    assert image_to_board(homography, tuple(bull)) == pytest.approx((0, 0), abs=1e-3)
    triple_20 = project(camera, [board_point(0, 103)])[0]
    assert dart_at(*image_to_board(homography, tuple(triple_20))) == Dart(20, 3)
