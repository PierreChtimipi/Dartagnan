"""Passage entre l'image d'une caméra et le plan de la cible, à partir des 4 points cliqués.

shortcut: homographie seule, sans correction de la distorsion de l'objectif (100°) ;
l'écart grandit loin des 4 points. Ajouter la calibration intrinsèque si la grille
projetée ne colle pas à la cible réelle.
"""

import cv2
import numpy as np

from dartagnan.geometry.board import CALIBRATION_POINTS

Point = tuple[float, float]


def board_to_image(image_points: list[Point]) -> np.ndarray:
    """Homographie qui envoie les mm de la cible vers les pixels de l'image."""
    return cv2.getPerspectiveTransform(
        np.float32(CALIBRATION_POINTS), np.float32(image_points)
    )


def project(homography: np.ndarray, points: list[Point]) -> np.ndarray:
    """Applique une homographie à une liste de points, résultat en tableau N x 2."""
    return cv2.perspectiveTransform(
        np.float32(points).reshape(-1, 1, 2), homography
    ).reshape(-1, 2)


def image_to_board(homography: np.ndarray, point: Point) -> Point:
    """Position en mm sur la cible d'un pixel de l'image, pour une homographie board_to_image."""
    x, y = project(np.linalg.inv(homography), [point])[0]
    return float(x), float(y)
