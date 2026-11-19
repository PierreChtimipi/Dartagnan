"""Détection automatique des points de la cible à partir des anneaux double et triple.

Les anneaux double et triple sont les seules zones rouges et vertes de la cible, et
leurs couleurs alternent à chaque secteur. L'image est déroulée en coordonnées polaires
à partir d'une homographie approchée : les bords des anneaux et les changements de
couleur donnent des dizaines de points, d'où une homographie recalée, plusieurs fois.

L'homographie approchée vient des 4 points cliqués, d'une calibration précédente, ou
de `initial_homography` (ellipse de l'anneau double et bull), avec l'orientation
approximative de la caméra (`top` dans `detect`).
Hypothèse : double et triple du 20 en rouge, comme sur les cibles classiques.
"""

import itertools
import math

import cv2
import numpy as np

from dartagnan.geometry.board import (
    DOUBLE_INNER_RADIUS,
    DOUBLE_OUTER_RADIUS,
    SECTOR_ANGLE,
    SECTORS,
    TRIPLE_INNER_RADIUS,
    TRIPLE_OUTER_RADIUS,
    board_point,
    sector_boundary,
)
from dartagnan.geometry.calibration import project

NONE, RED, GREEN = 0, 1, 2
STEP = 0.25  # pas d'échantillonnage polaire, en mm et en degrés
RINGS = (
    (TRIPLE_INNER_RADIUS, TRIPLE_OUTER_RADIUS),
    (DOUBLE_INNER_RADIUS, DOUBLE_OUTER_RADIUS),
)
SEARCH = 15.0  # mm de part et d'autre d'un anneau pour chercher ses bords
TOLERANCE = 2.0  # mm, écart au-delà duquel un point est écarté (RANSAC)


def color_labels(image: np.ndarray) -> np.ndarray:
    """Étiquette chaque pixel : RED, GREEN ou NONE. Seuils HSV réglés sur deux photos de
    cibles du commerce et les trois caméras du projet : teinte du rouge resserrée pour
    écarter l'orange (pieds de l'arceau, teinte 1 à 8), saturation basse pour un rouge
    délavé, vert jusqu'au turquoise (teinte 86 à 90)."""
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    labels = np.full(h.shape, NONE, np.uint8)
    labels[((h <= 3) | (h >= 165)) & (s >= 60) & (v >= 60)] = RED
    labels[(h >= 40) & (h <= 100) & (s >= 60) & (v >= 40)] = GREEN
    return labels


def _find_bull(labels: np.ndarray) -> np.ndarray | None:
    """Centre du bull (pixel homogène) : la tache rouge entourée de vert dans au moins
    7 directions sur 8. Un segment rouge du double ou du triple ne touche le vert qu'à
    ses deux extrémités. Les directions passent l'anneau de fil autour du bull."""
    count, _, stats, centroids = cv2.connectedComponentsWithStats(
        (labels == RED).astype(np.uint8)
    )
    height, width = labels.shape
    best, best_hits = None, 6
    for i in range(1, count):
        _, _, w, h, area = stats[i]
        if area < 4:
            continue
        cx, cy = centroids[i]
        steps = np.linspace(0, 1.5 * max(w, h), 30)
        hits = 0
        for angle in np.radians(np.arange(0, 360, 45)):
            xs = np.round(cx + steps * math.cos(angle)).astype(int)
            ys = np.round(cy + steps * math.sin(angle)).astype(int)
            inside = (xs >= 0) & (xs < width) & (ys >= 0) & (ys < height)
            hits += bool((labels[ys[inside], xs[inside]] == GREEN).any())
        if hits > best_hits:
            best, best_hits = centroids[i], hits
    return None if best is None else np.array([best[0], best[1], 1.0])


def initial_homography(labels: np.ndarray) -> np.ndarray | None:
    """Homographie approchée, juste à une rotation près : ellipse du bord extérieur du
    double et centre du bull. Le centre réel n'est pas celui de l'ellipse en perspective :
    sa polaire par rapport à l'ellipse est l'image de la droite à l'infini."""
    colored = (labels != NONE).astype(np.uint8)
    size = max(3, round(max(labels.shape) * 0.005))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    closed = cv2.morphologyEx(colored, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    (cx, cy), (w, h), angle = cv2.fitEllipse(max(contours, key=cv2.contourArea))
    a = math.radians(angle)
    rotation = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    ellipse = np.eye(3)  # cercle unité → ellipse
    ellipse[:2, :2] = rotation @ np.diag([w / 2, h / 2])
    ellipse[:2, 2] = (cx, cy)

    bull = _find_bull(labels)
    if bull is None:
        return None

    inverse = np.linalg.inv(ellipse)
    conic = inverse.T @ np.diag([1.0, 1.0, -1.0]) @ inverse
    horizon = conic @ bull
    rectify = np.eye(3)  # envoie l'horizon à l'infini
    rectify[2] = horizon / horizon[2]
    unrectify = np.linalg.inv(rectify)
    rectified = unrectify.T @ conic @ unrectify
    shape, offset = rectified[:2, :2], rectified[:2, 2]
    center = -np.linalg.solve(shape, offset)
    scale = offset @ np.linalg.solve(shape, offset) - rectified[2, 2]
    try:
        radius = np.linalg.cholesky(scale * np.linalg.inv(shape))  # cercle → ellipse
    except np.linalg.LinAlgError:
        return None  # « bull » hors de l'anneau : ce n'est pas une cible
    affine = np.eye(3)
    affine[:2, :2] = radius @ np.diag([1, -1]) / DOUBLE_OUTER_RADIUS
    affine[:2, 2] = center
    homography = unrectify @ affine
    # Vue en miroir si l'horizon sépare la cible de l'origine de l'image : une caméra
    # devant la cible la voit toujours dans le même sens (y de l'image vers le bas)
    center, right, up = project(homography, [(0, 0), (1, 0), (0, 1)])
    (ax, ay), (bx, by) = right - center, up - center
    if ax * by - ay * bx > 0:
        homography = homography @ np.diag([-1.0, 1.0, 1.0])
    return homography / homography[2, 2]


def _polar(labels: np.ndarray, homography: np.ndarray) -> np.ndarray:
    """Étiquettes rééchantillonnées : une ligne par rayon (mm), une colonne par angle (°)."""
    radii = np.arange(0, DOUBLE_OUTER_RADIUS + SEARCH, STEP)
    angles = np.radians(np.arange(0, 360, STEP))
    a, r = np.meshgrid(angles, radii)
    board = np.stack([r * np.sin(a), r * np.cos(a)], axis=-1).reshape(-1, 2)
    maps = project(homography, board).reshape(len(radii), len(angles), 2)
    return cv2.remap(
        labels, maps[..., 0], maps[..., 1], cv2.INTER_NEAREST, borderValue=NONE
    )


def _ring_edges(polar: np.ndarray) -> list[tuple[tuple, tuple]]:
    """Bords intérieur et extérieur des anneaux, mesurés degré par degré."""
    pairs = []
    for column in range(0, polar.shape[1], round(1 / STEP)):
        angle = column * STEP
        for inner, outer in RINGS:
            start = round((inner - SEARCH) / STEP)
            rows = np.flatnonzero(
                polar[start : round((outer + SEARCH) / STEP), column] != NONE
            )
            # Plus longue suite de lignes colorées : écarte logos et inscriptions voisins
            runs = np.split(rows, np.flatnonzero(np.diff(rows) > 3) + 1)
            run = max(runs, key=len)
            if len(run) < (outer - inner) / STEP / 2:
                continue  # fil ou anneau absent à cet angle
            for row, radius in ((run[0], inner), (run[-1] + 1, outer)):
                measured = (start + row) * STEP - STEP / 2
                pairs.append((board_point(angle, radius), board_point(angle, measured)))
    return pairs


def _ring_colors(polar: np.ndarray, inner: float, outer: float) -> np.ndarray:
    """Par angle, au milieu d'un anneau : +1 si rouge, -1 si vert, 0 si surtout ni l'un
    ni l'autre (fil métallique, fléchette, anneau absent)."""
    band = polar[round((inner + 2) / STEP) : round((outer - 2) / STEP)]
    red, green = (band == RED).sum(axis=0), (band == GREEN).sum(axis=0)
    colors = np.where(red > green, 1, -1)
    colors[np.maximum(red, green) < band.shape[0] / 2] = 0
    return colors


def _boundaries(polar: np.ndarray) -> list[tuple[tuple, tuple]]:
    """Limites des secteurs : changements rouge / vert au milieu de chaque anneau."""
    pairs = []
    half = round(SECTOR_ANGLE / 2 / STEP)
    size = polar.shape[1]
    for inner, outer in RINGS:
        middle = (inner + outer) / 2
        line = _ring_colors(polar, inner, outer)
        for i in range(len(SECTORS)):
            first = round(sector_boundary(i) / STEP) - half
            # (position dans la fenêtre, colonne) des angles colorés autour de la limite
            colored = [
                (k, (first + k) % size)
                for k in range(2 * half)
                if line[(first + k) % size] != 0
            ]
            changes = [
                (p + q) / 2
                for (p, a), (q, b) in itertools.pairwise(colored)
                if line[a] != line[b] and q - p < half
            ]
            if not changes:
                continue
            position = min(changes, key=lambda c: abs(c - half))
            measured = ((first + position) * STEP) % 360
            pairs.append(
                (board_point(sector_boundary(i), middle), board_point(measured, middle))
            )
    return pairs


def _color_signal(polar: np.ndarray) -> np.ndarray:
    """Par angle, somme des couleurs des deux anneaux (voir `_ring_colors`)."""
    return sum(_ring_colors(polar, inner, outer) for inner, outer in RINGS)


# Couleur attendue par angle : secteurs de rang pair (20, 18, 13...) en rouge
EXPECTED = np.array(
    [
        1.0 if int(((a + SECTOR_ANGLE / 2) % 360) // SECTOR_ANGLE) % 2 == 0 else -1.0
        for a in np.arange(0, 360, STEP)
    ]
)


def _align_rotation(
    labels: np.ndarray, homography: np.ndarray, top: float
) -> np.ndarray:
    """Tourne la cible pour que l'alternance rouge / vert corresponde à celle attendue,
    20 en rouge ; parmi les tours de 36° possibles, celui qui met l'angle `top` de la
    cible le plus près du haut de l'image."""
    signal = _color_signal(_polar(labels, homography))
    spectrum = np.fft.ifft(np.fft.fft(signal) * np.conj(np.fft.fft(EXPECTED))).real
    shift = int(np.argmax(spectrum)) * STEP

    def tilt(h: np.ndarray) -> float:
        center, edge = project(h, [(0, 0), board_point(top, DOUBLE_OUTER_RADIUS)])
        dx, dy = edge - center
        return abs(math.atan2(dx, -dy))

    turns = [_rotated(homography, shift + 2 * SECTOR_ANGLE * k) for k in range(10)]
    return min(turns, key=tilt)


def _rotated(homography: np.ndarray, degrees: float) -> np.ndarray:
    """Même homographie, cible tournée de `degrees`."""
    a = math.radians(degrees)
    turn = np.array(
        [[math.cos(a), math.sin(a), 0], [-math.sin(a), math.cos(a), 0], [0, 0, 1]]
    )
    return homography @ turn


def _fit_rings(
    labels: np.ndarray, homography: np.ndarray, iterations: int = 10
) -> tuple[np.ndarray, np.ndarray] | None:
    """Recale l'homographie sur les bords des anneaux seuls : chaque bord mesuré doit
    être à son rayon nominal (Gauss-Newton sur l'écart de rayon). Une homographie qui
    envoie les cercles de la cible sur leurs ellipses n'est juste qu'à une rotation près.
    Renvoie (homographie, écarts en mm des points retenus)."""
    for _ in range(iterations):
        pairs = _ring_edges(_polar(labels, homography))
        if len(pairs) < 8:
            return None
        nominal = np.array([math.hypot(*b) for b, _ in pairs])
        x, y = np.array([m for _, m in pairs]).T  # bords mesurés, repère actuel (mm)
        rho = np.hypot(x, y)
        residuals = rho - nominal
        # Points aberrants (logos, inscriptions) écartés
        kept = np.abs(residuals) <= max(TOLERANCE, 2.5 * np.median(np.abs(residuals)))
        if kept.sum() < 8:
            return None
        # Dérivées du rayon par rapport aux 8 coefficients de K = I + delta, x' = K x
        jacobian = np.column_stack(
            [x * x / rho, x * y / rho, x / rho, x * y / rho, y * y / rho, y / rho]
            + [-x * rho, -y * rho]
        )
        delta = np.linalg.lstsq(jacobian[kept], -residuals[kept], rcond=None)[0]
        step = np.append(delta, 0.0).reshape(3, 3) + np.eye(3)
        homography = homography @ np.linalg.inv(step)
        homography /= homography[2, 2]
        if np.abs(jacobian[kept] @ delta).max() < 0.02:
            break
    return homography, np.abs(residuals[kept])


def _fit_rotation(
    labels: np.ndarray, homography: np.ndarray
) -> tuple[np.ndarray, np.ndarray] | None:
    """Rotation fine : écart médian entre limites de secteurs mesurées et attendues.
    Renvoie (homographie, écarts en mm le long des anneaux)."""
    pairs = _boundaries(_polar(labels, homography))
    if len(pairs) < 4:
        return None
    offsets = np.array(
        [
            (math.degrees(math.atan2(*m) - math.atan2(*n)) + 180) % 360 - 180
            for n, m in pairs
        ]
    )
    offset = float(np.median(offsets))
    radii = np.array([math.hypot(*n) for n, _ in pairs])
    residuals = np.abs(np.radians(offsets - offset)) * radii
    return _rotated(homography, offset), residuals[residuals < TOLERANCE]


def refine(
    labels: np.ndarray, homography: np.ndarray
) -> tuple[np.ndarray, float, int] | None:
    """Recale une homographie juste à quelques degrés près. Renvoie (homographie, écart
    moyen en mm, nombre de points retenus), ou None si la cible n'est pas trouvée."""
    rings = _fit_rings(labels, homography)
    rotation = None if rings is None else _fit_rotation(labels, rings[0])
    if rotation is None:
        return None
    residuals = np.concatenate([rings[1], rotation[1]])
    return rotation[0], float(residuals.mean()), len(residuals)


def detect(
    labels: np.ndarray, homography: np.ndarray | None = None, top: float = 0.0
) -> tuple[np.ndarray, float, int] | None:
    """Détecte la cible. Sans homographie de départ : ellipse de l'anneau double et bull,
    calage sur les anneaux, puis rotation trouvée par l'alternance des couleurs.
    `top` : angle de la cible (degrés, sens horaire depuis le 20) attendu en haut de
    l'image, à 18° près ; 180 pour une caméra placée au-dessus du 20."""
    if homography is None:
        start = initial_homography(labels)
        rings = None if start is None else _fit_rings(labels, start)
        if rings is None:
            return None
        homography = _align_rotation(labels, rings[0], top)
    return refine(labels, homography)
