"""Axe d'une fléchette qui vient de se planter, dans la vue d'une caméra.

Prototype de la méthode « droites projetées » (point ouvert : méthode de détection à
valider par l'équipe). Différence entre les images d'avant et d'après le lancer : les
pixels qui ont changé sont ceux de la nouvelle fléchette, dont on ajuste l'axe.
"""

import cv2
import numpy as np


def dart_line(
    before: np.ndarray, after: np.ndarray, threshold: int = 30, min_area: int = 80
) -> np.ndarray | None:
    """Droite de l'axe de la fléchette dans l'image, en coordonnées homogènes (a, b, c),
    a x + b y + c = 0. None si le changement entre les deux images est trop petit, ou
    trop grand pour être une fléchette."""
    changed = (cv2.absdiff(before, after).max(axis=2) > threshold).astype(np.uint8)
    changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    ys, xs = np.nonzero(changed)
    # Une fléchette couvre au plus quelques % de l'image (3,6 % en simulation, près
    # d'une caméra) : au-delà de 15 %, changement de lumière ou passage
    if not min_area <= len(xs) <= changed.size * 0.15:
        return None
    points = np.column_stack([xs, ys]).astype(np.float32)
    vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
    return np.cross([x0, y0, 1.0], [x0 + vx, y0 + vy, 1.0])
