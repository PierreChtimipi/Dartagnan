"""Position de la pointe à partir des axes de la fléchette vus par plusieurs caméras.

L'homographie d'une caméra envoie chaque point de l'image sur le plan de la cible, le
long du rayon de la caméra. L'axe de la fléchette, projeté ainsi, devient une droite
de la cible qui passe par la pointe (seul point de l'axe dans le plan). Les droites de
plusieurs caméras se coupent donc à la pointe, même si celle-ci est masquée dans une vue.
"""

import math

import numpy as np


def board_line(homography: np.ndarray, image_line: np.ndarray) -> np.ndarray:
    """Droite de la cible (mm), normalisée : a x + b y + c est une distance en mm."""
    line = homography.T @ image_line
    return line / math.hypot(line[0], line[1])


def intersect(lines: list[np.ndarray]) -> tuple[tuple[float, float], float] | None:
    """Point le plus proche de toutes les droites (moindres carrés) et plus grande
    distance de ce point à une droite (mm). None avec moins de deux droites."""
    if len(lines) < 2:
        return None
    a = np.array(lines)
    point = np.linalg.lstsq(a[:, :2], -a[:, 2], rcond=None)[0]
    spread = float(np.abs(a[:, :2] @ point + a[:, 2]).max())
    return (float(point[0]), float(point[1])), spread
