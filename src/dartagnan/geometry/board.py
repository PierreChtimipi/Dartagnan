"""Géométrie de la cible : dimensions, ordre des secteurs, zone touchée en un point.

Seul endroit du code où sont définies les dimensions de la cible.
Repère en mm : origine au centre, x vers la droite, y vers le haut.
"""

import math

from dartagnan.game.darts import BULL, MISS, Dart

# Sens horaire depuis le haut, le 20 centré sur la verticale
SECTORS = (20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5)
SECTOR_ANGLE = 360 / len(SECTORS)

# Rayons en mm depuis le centre
BULL_RADIUS = 6.35
OUTER_BULL_RADIUS = 15.9
TRIPLE_INNER_RADIUS = 99.0
TRIPLE_OUTER_RADIUS = 107.0
DOUBLE_INNER_RADIUS = 162.0
DOUBLE_OUTER_RADIUS = 170.0
RING_RADII = (
    BULL_RADIUS,
    OUTER_BULL_RADIUS,
    TRIPLE_INNER_RADIUS,
    TRIPLE_OUTER_RADIUS,
    DOUBLE_INNER_RADIUS,
    DOUBLE_OUTER_RADIUS,
)


def sector_boundary(index: int) -> float:
    """Angle en degrés, sens horaire depuis le haut, de la limite entre SECTORS[index] et le suivant."""
    return SECTOR_ANGLE / 2 + index * SECTOR_ANGLE


def board_point(angle: float, radius: float) -> tuple[float, float]:
    """Point de la cible à un angle (degrés, sens horaire depuis le haut) et un rayon (mm)."""
    a = math.radians(angle)
    return radius * math.sin(a), radius * math.cos(a)


# Points de calibration : bord extérieur du double aux limites 20|1, 6|10, 3|19, 11|14
CALIBRATION_LABELS = ("20 | 1", "6 | 10", "3 | 19", "11 | 14")
CALIBRATION_POINTS = tuple(
    board_point(sector_boundary(i), DOUBLE_OUTER_RADIUS) for i in (0, 5, 10, 15)
)


def dart_at(x: float, y: float) -> Dart:
    """Zone touchée au point (x, y) en mm. Chaque limite appartient à la zone extérieure."""
    radius = math.hypot(x, y)
    if radius >= DOUBLE_OUTER_RADIUS:
        return Dart(MISS, 1)
    if radius < BULL_RADIUS:
        return Dart(BULL, 2)
    if radius < OUTER_BULL_RADIUS:
        return Dart(BULL, 1)
    angle = (math.degrees(math.atan2(x, y)) + SECTOR_ANGLE / 2) % 360
    sector = SECTORS[int(angle // SECTOR_ANGLE)]
    if TRIPLE_INNER_RADIUS <= radius < TRIPLE_OUTER_RADIUS:
        return Dart(sector, 3)
    if radius >= DOUBLE_INNER_RADIUS:
        return Dart(sector, 2)
    return Dart(sector, 1)
