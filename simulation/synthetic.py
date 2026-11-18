"""Vues simulées des caméras autour de la cible, pour développer sans matériel.

Repère 3D en mm : cible dans le plan z = 0 (x vers la droite, y vers le haut, comme
`geometry.board`), z vers le lanceur. Caméras sans distorsion d'objectif (sténopé).

Position des caméras : hypothèses à confirmer avec la conception de l'arceau.
"""

import math
from dataclasses import dataclass

import cv2
import numpy as np

from dartagnan.geometry.board import (
    BULL_RADIUS,
    DOUBLE_INNER_RADIUS,
    DOUBLE_OUTER_RADIUS,
    OUTER_BULL_RADIUS,
    SECTOR_ANGLE,
    SECTORS,
    TRIPLE_INNER_RADIUS,
    TRIPLE_OUTER_RADIUS,
)

# Hypothèses à confirmer : caméras au droit du 20, du 16 et du 15, visées vers le centre
CAMERA_SECTORS = (20, 16, 15)
CAMERA_DISTANCE = 250.0  # mm, depuis l'axe de la cible
CAMERA_HEIGHT = 60.0  # mm, devant la surface de la cible
FOV_DIAGONAL = 100.0  # degrés, OV9732 (diagonale à confirmer)
WIDTH, HEIGHT = 1280, 720
BOARD_EDGE = 225.0  # mm, bord du support noir autour de la zone de score

RED, GREEN = (40, 40, 200), (40, 150, 30)
BLACK, CREAM, WALL = (25, 25, 25), (175, 215, 230), (200, 200, 200)

# Fléchette : (début, fin) le long de l'axe depuis la pointe en mm, rayon en mm, couleur
DART_PARTS = (
    (0.0, 30.0, 1.0, (170, 170, 170)),  # pointe
    (30.0, 75.0, 3.5, (70, 70, 70)),  # fût
    (75.0, 110.0, 2.0, (160, 70, 30)),  # tige
)
FLIGHT = (105.0, 145.0, 15.0, (40, 140, 230))  # ailettes : début, fin, demi-largeur


def board_colors(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Couleur BGR de la cible en chaque point (mm) : 20 en noir, double et triple du 20
    en rouge, comme une cible classique."""
    radius = np.hypot(x, y)
    sector = ((np.degrees(np.arctan2(x, y)) + SECTOR_ANGLE / 2) % 360) // SECTOR_ANGLE
    even = sector % 2 == 0
    ring = ((radius >= TRIPLE_INNER_RADIUS) & (radius < TRIPLE_OUTER_RADIUS)) | (
        (radius >= DOUBLE_INNER_RADIUS) & (radius < DOUBLE_OUTER_RADIUS)
    )
    colors = np.where(even[..., None], BLACK, CREAM)
    colors[ring] = np.where(even[ring, None], RED, GREEN)
    colors[radius < OUTER_BULL_RADIUS] = GREEN
    colors[radius < BULL_RADIUS] = RED
    colors[radius >= DOUBLE_OUTER_RADIUS] = BLACK
    colors[radius >= BOARD_EDGE] = WALL
    return colors.astype(np.uint8)


@dataclass(frozen=True)
class SimulatedCamera:
    """Caméra sténopé : matrice intrinsèque, rotation monde → caméra, centre optique."""

    intrinsics: np.ndarray
    rotation: np.ndarray
    center: np.ndarray

    @classmethod
    def around_board(
        cls,
        sector: int,
        distance: float = CAMERA_DISTANCE,
        height: float = CAMERA_HEIGHT,
        fov_diagonal: float = FOV_DIAGONAL,
    ) -> "SimulatedCamera":
        """Caméra au droit d'un secteur, visée vers le centre, image droite (le lanceur
        vers le haut de l'image)."""
        angle = math.radians(SECTORS.index(sector) * SECTOR_ANGLE)
        center = np.array(
            [distance * math.sin(angle), distance * math.cos(angle), height]
        )
        forward = -center / np.linalg.norm(center)
        right = np.cross(forward, [0.0, 0.0, 1.0])
        right /= np.linalg.norm(right)
        down = np.cross(forward, right)
        focal = math.hypot(WIDTH, HEIGHT) / 2 / math.tan(math.radians(fov_diagonal) / 2)
        intrinsics = np.array(
            [[focal, 0, WIDTH / 2], [0, focal, HEIGHT / 2], [0, 0, 1]]
        )
        return cls(intrinsics, np.array([right, down, forward]), center)

    @property
    def homography(self) -> np.ndarray:
        """Homographie exacte du plan de la cible (mm) vers l'image."""
        r = self.rotation
        h = self.intrinsics @ np.column_stack([r[:, 0], r[:, 1], -r @ self.center])
        return h / h[2, 2]

    def project(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Pixels et profondeurs (mm) de points 3D."""
        camera = (np.atleast_2d(points) - self.center) @ self.rotation.T
        pixels = camera @ self.intrinsics.T
        return pixels[:, :2] / pixels[:, 2:], camera[:, 2]


def render_board(camera: SimulatedCamera) -> np.ndarray:
    """Vue de la cible vide : lancer de rayons sur le plan z = 0."""
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    pixels = np.stack([xs, ys, np.ones_like(xs)], axis=-1).reshape(-1, 3)
    rays = pixels @ np.linalg.inv(camera.intrinsics).T @ camera.rotation
    hits = rays[:, 2] < 0
    image = np.full((len(rays), 3), WALL, np.uint8)
    t = -camera.center[2] / rays[hits, 2]
    x = camera.center[0] + t * rays[hits, 0]
    y = camera.center[1] + t * rays[hits, 1]
    image[hits] = board_colors(x, y)
    return image.reshape(HEIGHT, WIDTH, 3)


def draw_dart(
    image: np.ndarray,
    camera: SimulatedCamera,
    tip: tuple[float, float],
    axis: np.ndarray,
) -> None:
    """Dessine une fléchette plantée en `tip` (mm), `axis` : direction vers l'arrière."""
    axis = axis / np.linalg.norm(axis)
    origin = np.array([tip[0], tip[1], 0.0])
    side = np.cross(axis, [0.0, 0.0, 1.0])
    side = (
        side / np.linalg.norm(side)
        if np.linalg.norm(side) > 1e-6
        else np.array([1.0, 0, 0])
    )
    lift = np.cross(axis, side)
    start, end, half, color = FLIGHT
    for wing in (side, lift):
        corners = [
            origin + axis * start + wing * half,
            origin + axis * end + wing * half,
            origin + axis * end - wing * half,
            origin + axis * start - wing * half,
        ]
        pixels, _ = camera.project(np.array(corners))
        cv2.fillPoly(image, [np.round(pixels).astype(np.int32)], color, cv2.LINE_AA)
    for start, end, radius, color in reversed(DART_PARTS):
        steps = np.linspace(start, end, 8)
        points = origin + steps[:, None] * axis
        pixels, depths = camera.project(points)
        for i in range(len(steps) - 1):
            width = max(1, round(2 * radius * camera.intrinsics[0, 0] / depths[i]))
            a, b = (tuple(np.round(p).astype(int)) for p in pixels[i : i + 2])
            cv2.line(image, a, b, color, width, cv2.LINE_AA)


def dart_axis(rng: np.random.Generator) -> np.ndarray:
    """Axe d'une fléchette plantée, vers l'arrière : 5 à 25° de la normale à la cible."""
    tilt = math.radians(rng.uniform(5, 25))
    heading = math.radians(rng.uniform(-40, 40))
    return np.array(
        [
            math.sin(tilt) * math.sin(heading),
            math.sin(tilt) * math.cos(heading),
            math.cos(tilt),
        ]
    )


def noisy(
    image: np.ndarray, rng: np.random.Generator, sigma: float = 2.0
) -> np.ndarray:
    """Bruit de capteur gaussien."""
    noise = rng.normal(0, sigma, image.shape)
    return np.clip(image + noise, 0, 255).astype(np.uint8)
