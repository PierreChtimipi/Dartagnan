import math

import numpy as np
import pytest

from dartagnan.detection.dart import dart_line
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
