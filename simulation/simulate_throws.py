"""Simulation de la chaîne de détection complète avec trois caméras virtuelles.

Caméras au droit du 20, du 16 et du 15 (hypothèses de `synthetic.py`, à
confirmer). Pour chaque caméra : calibration automatique sur la vue de la cible vide.
Pour chaque fléchette : axe repéré par différence d'images dans chaque vue, droites
projetées sur la cible, intersection, score. Résultats comparés à la position réelle.

    $env:PYTHONPATH="src"; $env:DARTAGNAN_DATA="data"
    .venv\\Scripts\\python simulation\\simulate_throws.py --volleys 10

Images des premières volées (3 vues et cible de face) dans $DARTAGNAN_DATA/simulation/.
"""

import argparse
import math
import os
from pathlib import Path

import cv2
import numpy as np
import synthetic
from synthetic import SimulatedCamera

from dartagnan.detection.dart import dart_line
from dartagnan.geometry.auto_calibration import color_labels, detect
from dartagnan.geometry.board import (
    DOUBLE_OUTER_RADIUS,
    SECTOR_ANGLE,
    SECTORS,
    board_point,
    dart_at,
)
from dartagnan.geometry.calibration import image_to_board, project
from dartagnan.geometry.triangulation import board_line, intersect

COLORS = ((255, 0, 255), (255, 255, 0), (0, 255, 255))  # une couleur par caméra
SCALE = 2.0  # px par mm de la vue de face
HALF = 230.0  # mm affichés de part et d'autre du centre
SIZE = round(2 * HALF * SCALE)


def calibrate(
    camera: SimulatedCamera, sector: int, rng: np.random.Generator
) -> tuple[np.ndarray, float]:
    """Calibration automatique de la vue vide ; erreur réelle maximale en mm."""
    top = (SECTORS.index(sector) * SECTOR_ANGLE + 180) % 360
    view = synthetic.noisy(synthetic.render_board(camera), rng)
    result = detect(color_labels(view), top=top)
    if result is None:
        raise SystemExit(
            f"Calibration automatique impossible pour la caméra du {sector}"
        )
    found = result[0]
    checks = [board_point(a, r) for a in range(0, 360, 10) for r in (0, 100, 166)]
    error = max(
        math.dist(image_to_board(found, tuple(project(camera.homography, [p])[0])), p)
        for p in checks
    )
    return found, error


def line_ends(line: np.ndarray, width: int, height: int) -> list[tuple[int, int]]:
    """Extrémités d'une droite homogène dans un rectangle, pour la dessiner."""
    a, b, c = line
    ends = []
    for x in (0, width):
        if abs(b) > 1e-9 and 0 <= (y := -(a * x + c) / b) <= height:
            ends.append((round(x), round(y)))
    for y in (0, height):
        if abs(a) > 1e-9 and 0 <= (x := -(b * y + c) / a) <= width:
            ends.append((round(x), round(y)))
    return ends[:2]


def to_front(point: tuple[float, float]) -> tuple[int, int]:
    """Pixel de la vue de face d'un point de la cible (mm)."""
    return round((point[0] + HALF) * SCALE), round((HALF - point[1]) * SCALE)


def front_line(line: np.ndarray) -> np.ndarray:
    """Droite de la cible (mm) exprimée en pixels de la vue de face."""
    a, b, c = line
    return np.array([a / SCALE, -b / SCALE, c - a * HALF + b * HALF])


def front_view() -> np.ndarray:
    """Cible de face, 20 en haut, numéros des secteurs."""
    v, u = np.mgrid[0:SIZE, 0:SIZE]
    image = synthetic.board_colors(u / SCALE - HALF, HALF - v / SCALE)
    for i, sector in enumerate(SECTORS):
        x, y = to_front(board_point(i * SECTOR_ANGLE, DOUBLE_OUTER_RADIUS + 28))
        cv2.putText(
            image,
            str(sector),
            (x - 12, y + 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
    return image


def save_volley(path: Path, scenes: list, drawn: list, front: np.ndarray) -> None:
    """Les trois vues avec l'axe détecté de chaque fléchette, et la cible de face."""
    views = []
    for i, scene in enumerate(scenes):
        view = scene.copy()
        for line in drawn[i]:
            ends = line_ends(line, view.shape[1], view.shape[0])
            if len(ends) == 2:
                cv2.line(view, ends[0], ends[1], COLORS[i], 2)
        views.append(cv2.resize(view, (640, 360)))
    column = np.vstack(views)
    canvas = np.full((column.shape[0], 640 + column.shape[0], 3), 255, np.uint8)
    canvas[:, :640] = column
    canvas[:, 640:] = cv2.resize(front, (column.shape[0], column.shape[0]))
    # cv2.imwrite échoue sans erreur, par exemple sur un chemin accentué
    if not cv2.imwrite(str(path), canvas):
        print(f"Échec de l'enregistrement : {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--volleys", type=int, default=10, help="volées de 3 fléchettes"
    )
    parser.add_argument(
        "--save", type=int, default=3, help="volées enregistrées en image"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--distance", type=float, default=synthetic.CAMERA_DISTANCE)
    parser.add_argument("--height", type=float, default=synthetic.CAMERA_HEIGHT)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    output = Path(os.environ.get("DARTAGNAN_DATA", "/var/lib/dartagnan")) / "simulation"
    output.mkdir(parents=True, exist_ok=True)
    cameras = [
        SimulatedCamera.around_board(s, args.distance, args.height)
        for s in synthetic.CAMERA_SECTORS
    ]
    homographies = []
    for sector, camera in zip(synthetic.CAMERA_SECTORS, cameras):
        found, error = calibrate(camera, sector, rng)
        homographies.append(found)
        print(f"Caméra du {sector:>2} : calibrée, erreur réelle max {error:.2f} mm")

    errors, right = [], 0
    for volley in range(args.volleys):
        scenes = [synthetic.render_board(c) for c in cameras]
        before = [synthetic.noisy(s, rng) for s in scenes]
        front = front_view()
        drawn: list[list[np.ndarray]] = [[] for _ in cameras]
        for _ in range(3):
            tip = board_point(rng.uniform(0, 360), 168 * math.sqrt(rng.uniform()))
            axis = synthetic.dart_axis(rng)
            lines = []
            for i, camera in enumerate(cameras):
                synthetic.draw_dart(scenes[i], camera, tip, axis)
                after = synthetic.noisy(scenes[i], rng)
                found = dart_line(before[i], after)
                before[i] = after
                if found is None:
                    continue
                drawn[i].append(found)
                lines.append(board_line(homographies[i], found))
                ends = line_ends(front_line(lines[-1]), SIZE, SIZE)
                if len(ends) == 2:
                    cv2.line(front, ends[0], ends[1], COLORS[i], 1, cv2.LINE_AA)
            truth = dart_at(*tip)
            result = intersect(lines)
            if result is None:
                print(f"Volée {volley + 1} : {truth.label:>5} non détectée")
                continue
            point, spread = result
            dart = dart_at(*point)
            errors.append(math.dist(point, tip))
            right += dart == truth
            print(
                f"Volée {volley + 1} : réel {truth.label:>5}  détecté {dart.label:>5}"
                f"  erreur {errors[-1]:4.1f} mm  écart entre droites {spread:4.1f} mm"
            )
            cv2.circle(front, to_front(tip), 7, (255, 255, 255), 2)
            x, y = to_front(point)
            cv2.drawMarker(front, (x, y), (0, 0, 255), cv2.MARKER_CROSS, 16, 2)
            cv2.putText(
                front,
                dart.label,
                (x + 10, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
        if volley < args.save:
            save_volley(output / f"volley_{volley + 1}.png", scenes, drawn, front)

    if errors:
        print(
            f"\n{right}/{len(errors)} zones justes, erreur moyenne {np.mean(errors):.1f}"
            f" mm, max {np.max(errors):.1f} mm"
        )
    print(f"Images : {output}")


if __name__ == "__main__":
    main()
