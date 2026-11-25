"""Déclenchement à l'impact : repère le moment où une fléchette vient de se planter.

Chaque caméra mesure en continu la part de la cible qui change d'une image à la suivante.
Une fléchette qui arrive fait bouger l'image ; quand l'image redevient stable, la
fléchette est plantée et la détection peut comparer l'image d'avant et celle d'après.
"""

import cv2
import numpy as np

SMALL = 0.25  # images réduites au quart pour mesurer le mouvement à moindre coût


def small_gray(image: np.ndarray) -> np.ndarray:
    """Image réduite en niveaux de gris, lissée contre le bruit du capteur."""
    gray = cv2.cvtColor(cv2.resize(image, None, fx=SMALL, fy=SMALL), cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def motion(previous: np.ndarray, current: np.ndarray, mask: np.ndarray) -> float:
    """Part des pixels de la cible (`mask` non nul) qui changent entre deux images
    réduites (`small_gray`), de 0 à 1."""
    changed = (cv2.absdiff(previous, current) > 25) & (mask > 0)
    return float(changed.sum()) / max(int((mask > 0).sum()), 1)


class ImpactTrigger:
    """Renvoie True une seule fois, quand l'image redevient stable après avoir bougé.

    `moving` : part de la cible au-delà de laquelle l'image bouge ; `still` : en deçà,
    elle est calme ; `still_frames` : nombre d'images calmes d'affilée pour la déclarer
    stable (10 images, environ 0,35 s à 28 images par seconde)."""

    def __init__(
        self, moving: float = 0.002, still: float = 0.0005, still_frames: int = 10
    ) -> None:
        self.moving, self.still, self.still_frames = moving, still, still_frames
        self.reset()

    def reset(self) -> None:
        self.moved = False
        self.calm = 0

    def update(self, amount: float) -> bool:
        """`amount` : mouvement de l'image courante (le plus fort des caméras)."""
        if amount > self.moving:
            self.moved, self.calm = True, 0
            return False
        self.calm = self.calm + 1 if amount < self.still else 0
        if self.moved and self.calm >= self.still_frames:
            self.reset()
            return True
        return False
