import math

import cv2
import numpy as np
import pytest

from dartagnan.detection.dart import board_mask, dart_line
from dartagnan.geometry.triangulation import intersect


def test_intersection_de_droites():
    lines = [
        np.array([math.cos(a), math.sin(a), -(math.cos(a) * 12 - math.sin(a) * 30)])
        for a in (0.3, 1.5, 2.6)
    ]
    found, spread = intersect(lines)
    assert found == pytest.approx((12.0, -30.0))
    assert spread == pytest.approx(0, abs=1e-9)
    assert intersect(lines[:1]) is None


def test_aucun_changement_aucune_droite():
    image = np.full((720, 1280, 3), 100, np.uint8)
    assert dart_line(image, image.copy()) is None


def test_changement_de_luminosite_n_est_pas_une_flechette():
    before = np.full((720, 1280, 3), 100, np.uint8)
    assert dart_line(before, before + 40) is None


def test_masque_de_la_cible_ecarte_l_arriere_plan():
    # Cible vue de face : 1,5 px par mm, centre au milieu de l'image
    homography = np.array([[1.5, 0, 640], [0, -1.5, 360], [0, 0, 1]])
    mask = board_mask(homography, (720, 1280, 3))
    assert mask[360, 640] == 1 and mask[0, 0] == 0
    before = np.full((720, 1280, 3), 100, np.uint8)
    after = before.copy()
    cv2.line(after, (600, 300), (700, 200), (20, 20, 20), 6)  # fléchette sur la cible
    after[0:200, 0:200] = 200  # personne qui passe derrière la cible
    a, b, c = dart_line(before, after, mask)
    for x, y in ((600, 300), (650, 250), (700, 200)):
        assert abs(a * x + b * y + c) / math.hypot(a, b) < 2
