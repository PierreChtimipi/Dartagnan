import math

import cv2
import numpy as np
import pytest

from dartagnan.geometry.auto_calibration import color_labels, detect
from dartagnan.geometry.board import (
    BULL_RADIUS,
    CALIBRATION_POINTS,
    DOUBLE_INNER_RADIUS,
    DOUBLE_OUTER_RADIUS,
    OUTER_BULL_RADIUS,
    SECTOR_ANGLE,
    TRIPLE_INNER_RADIUS,
    TRIPLE_OUTER_RADIUS,
    board_point,
)
from dartagnan.geometry.calibration import board_to_image, image_to_board, project

# Cible vue de biais, 20 incliné d'environ 11° (moins de 18° : voir detect)
CAMERA = np.array([[1.2, 0.3, 640], [0.05, -0.8, 360], [0.0005, 0.0008, 1]])
RED, GREEN, BLACK, CREAM = (40, 40, 200), (40, 150, 30), (25, 25, 25), (175, 215, 230)


def render(homography: np.ndarray) -> np.ndarray:
    """Image 1280 x 720 d'une cible classique (20 en rouge) vue par l'homographie."""
    ys, xs = np.mgrid[0:720, 0:1280]
    pixels = np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float64)
    x, y = project(np.linalg.inv(homography), pixels).T
    radius = np.hypot(x, y)
    sector = ((np.degrees(np.arctan2(x, y)) + SECTOR_ANGLE / 2) % 360) // SECTOR_ANGLE
    even = sector % 2 == 0
    ring = ((radius >= TRIPLE_INNER_RADIUS) & (radius < TRIPLE_OUTER_RADIUS)) | (
        (radius >= DOUBLE_INNER_RADIUS) & (radius < DOUBLE_OUTER_RADIUS)
    )
    image = np.full((len(x), 3), 90, np.uint8)
    image[radius < 225] = BLACK
    image[(radius < DOUBLE_OUTER_RADIUS) & ~even] = CREAM
    image[ring] = np.where(even[ring, None], RED, GREEN)
    image[radius < OUTER_BULL_RADIUS] = GREEN
    image[radius < BULL_RADIUS] = RED
    return image.reshape(720, 1280, 3)


def max_error(found: np.ndarray, true: np.ndarray) -> float:
    checks = [board_point(a, r) for a in range(0, 360, 30) for r in (0, 103, 166)]
    return max(
        math.dist(image_to_board(found, tuple(project(true, [p])[0])), p)
        for p in checks
    )


@pytest.fixture(scope="module")
def labels() -> np.ndarray:
    return color_labels(render(CAMERA))


def test_detection_sans_point_de_depart(labels):
    found, error, kept = detect(labels)
    assert error < 1.0 and kept > 100
    assert max_error(found, CAMERA) < 1.0


def test_recalage_de_clics_approximatifs(labels):
    offsets = [(6, -4), (-5, 7), (4, 5), (-7, -3)]
    clicked = project(CAMERA, list(CALIBRATION_POINTS)) + offsets
    found, _, _ = detect(labels, board_to_image([tuple(p) for p in clicked]))
    assert max_error(found, CAMERA) < 1.0


def test_image_sans_cible():
    assert detect(color_labels(np.full((720, 1280, 3), 90, np.uint8))) is None


def test_tache_rouge_et_verte_hors_d_un_anneau():
    image = np.full((720, 1280, 3), 90, np.uint8)
    cv2.ellipse(image, (640, 360), (300, 200), 0, 0, 360, (0, 150, 0), 12)
    cv2.circle(image, (1150, 650), 25, (0, 150, 0), -1)
    cv2.circle(image, (1150, 650), 10, (0, 0, 220), -1)
    assert detect(color_labels(image)) is None
