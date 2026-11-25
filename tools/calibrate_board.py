"""Placement des points de calibration de la cible sur l'image de chaque caméra.

Pour chaque caméra, cliquer les 4 points demandés sur le bord extérieur du double,
aux limites 20|1, 6|10, 3|19 et 11|14. La grille de la cible est alors projetée sur
l'image et doit coller aux fils de la cible ; glisser un point pour l'ajuster.
Le survol de la souris affiche la zone visée (T20, D5, Bull...).

Touche A : détection automatique de la cible par les couleurs des anneaux. Sans point
placé, elle part de zéro : `--top` donne, pour chaque source, l'angle de la cible
(degrés, sens horaire depuis le 20) attendu en haut de l'image, à 18° près. Caméras au
droit du 20, du 16 et du 15 visées vers le centre : `--top 180 54 306`. Avec 4 points
placés, même approximatifs, elle les recale sans avoir besoin de `--top`.

Sur PC Windows, caméras par numéro :
    DARTAGNAN_DATA=data PYTHONPATH=src .venv/Scripts/python tools/calibrate_board.py 0 1 2

Une source peut aussi être une image ou une vidéo enregistrée.
Touches : A détection automatique, Tab caméra suivante, R efface les points,
P photo de chaque caméra, S enregistre, Q ou Échap quitte.

Fenêtre OpenCV : outil de développement sur PC, inutilisable sur la Pi sans bureau.
"""

import argparse
import json
import math
import os
import time
from pathlib import Path

import cv2
import numpy as np

from dartagnan.capture.camera import Camera, find_cameras
from dartagnan.geometry.auto_calibration import color_labels, detect
from dartagnan.geometry.board import (
    CALIBRATION_LABELS,
    CALIBRATION_POINTS,
    DOUBLE_OUTER_RADIUS,
    OUTER_BULL_RADIUS,
    RING_RADII,
    SECTOR_ANGLE,
    SECTORS,
    board_point,
    dart_at,
    sector_boundary,
)
from dartagnan.geometry.calibration import board_to_image, image_to_board, project

WINDOW = "Calibration"
SCREEN = (1280, 720)  # taille de fenêtre maximale à l'ouverture, redimensionnable
GRAB_DISTANCE = 20  # px à l'écran : un clic plus proche d'un point placé le déplace
GRID = (0, 255, 0)
MARK = (0, 255, 255)


def zoom(image: np.ndarray) -> float:
    """Agrandissement des traits et textes, pour qu'une grande image réduite à l'écran
    reste lisible."""
    return max(1.0, image.shape[1] / SCREEN[0], image.shape[0] / SCREEN[1])


def text(
    image: np.ndarray,
    label: str,
    org: tuple[float, float],
    color: tuple[int, int, int] = MARK,
) -> None:
    # Polices Hershey d'OpenCV : pas d'accents dans les textes affichés
    z = zoom(image)
    at = (round(org[0]), round(org[1]))
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, label, at, font, 0.6 * z, (0, 0, 0), round(4 * z))
    cv2.putText(image, label, at, font, 0.6 * z, color, round(z))


def draw_board(image: np.ndarray, homography: np.ndarray) -> None:
    """Projette les anneaux, les limites et les numéros des secteurs sur l'image."""
    z = zoom(image)
    width = round(z)
    for radius in RING_RADII:
        ring = project(homography, [board_point(a, radius) for a in range(0, 360, 2)])
        cv2.polylines(image, [ring.astype(np.int32)], True, GRID, width, cv2.LINE_AA)
    for i, sector in enumerate(SECTORS):
        angle = sector_boundary(i)
        ends = project(
            homography,
            [
                board_point(angle, OUTER_BULL_RADIUS),
                board_point(angle, DOUBLE_OUTER_RADIUS),
            ],
        ).astype(int)
        cv2.line(image, tuple(ends[0]), tuple(ends[1]), GRID, width, cv2.LINE_AA)
        x, y = project(
            homography, [board_point(i * SECTOR_ANGLE, DOUBLE_OUTER_RADIUS + 15)]
        )[0]
        text(image, str(sector), (x - 10 * z, y + 5 * z), GRID)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "sources",
        nargs="*",
        help="numéros de caméra (PC), chemins by-path, images ou vidéos (défaut : by-path)",
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--top",
        type=float,
        nargs="+",
        help="angle de la cible en haut de l'image, un par source (défaut : 0, le 20)",
    )
    args = parser.parse_args()

    sources = args.sources or find_cameras()
    if not sources:
        raise SystemExit(
            "Aucune source : donner les numéros des caméras, par exemple 0 1 2"
        )
    tops = args.top or [0.0] * len(sources)
    if len(tops) != len(sources):
        raise SystemExit(f"--top : {len(sources)} valeurs attendues, une par source")
    data_dir = Path(os.environ.get("DARTAGNAN_DATA", "/var/lib/dartagnan"))
    path = data_dir / "calibration.json"

    points: list[list[tuple[float, float]]] = [[] for _ in sources]
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))["cameras"]
        for i, camera in enumerate(saved[: len(sources)]):
            points[i] = [tuple(p) for p in camera["points"]]
            print(
                f"Points repris de {path} pour la caméra {i + 1} ({camera['source']})"
            )

    cameras = [Camera(s, args.width, args.height, args.fps) for s in sources]
    state = {"current": 0, "drag": None, "mouse": None, "zoom": 1.0, "shape": None}

    def on_mouse(event: int, x: int, y: int, flags: int, param: object) -> None:
        state["mouse"] = (x, y)
        placed = points[state["current"]]
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(placed) < 4:
                placed.append((x, y))
                return
            nearest = min(range(4), key=lambda i: math.dist(placed[i], (x, y)))
            if math.dist(placed[nearest], (x, y)) <= GRAB_DISTANCE * state["zoom"]:
                state["drag"] = nearest
        elif event == cv2.EVENT_MOUSEMOVE and state["drag"] is not None:
            placed[state["drag"]] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            state["drag"] = None

    # Fenêtre redimensionnable : les clics restent en pixels de l'image
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, on_mouse)
    try:
        while True:
            index = state["current"]
            camera, placed = cameras[index], points[index]
            frame = camera.frame
            image = (
                np.zeros((args.height, args.width, 3), np.uint8)
                if frame is None
                else frame.copy()
            )
            z = state["zoom"] = zoom(image)
            if image.shape != state["shape"]:
                # Nouvelle taille d'image : fenêtre ramenée à l'écran, proportions gardées
                state["shape"] = image.shape
                height, width = image.shape[:2]
                cv2.resizeWindow(WINDOW, round(width / z), round(height / z))
            if len(placed) == 4:
                homography = board_to_image(placed)
                draw_board(image, homography)
                if state["mouse"] is not None:
                    x, y = image_to_board(homography, state["mouse"])
                    dart = dart_at(x, y)
                    label = dart.label if dart.segment else "Hors cible"
                    mx, my = state["mouse"]
                    text(
                        image,
                        f"{label}  ({x:.0f}, {y:.0f}) mm",
                        (mx + 15 * z, my - 15 * z),
                    )
            for i, (px, py) in enumerate(placed):
                cv2.circle(image, (int(px), int(py)), round(6 * z), MARK, round(2 * z))
                text(image, CALIBRATION_LABELS[i], (px + 10 * z, py - 10 * z))

            name = f"Camera {index + 1}/{len(cameras)} : {camera.name}"
            text(image, name, (10 * z, 25 * z))
            if len(placed) < 4:
                text(
                    image,
                    f"Cliquer le bord exterieur du double, limite {CALIBRATION_LABELS[len(placed)]}",
                    (10 * z, 50 * z),
                )
            text(
                image,
                "A auto  Tab camera suivante  R effacer  P photo  S enregistrer  Q quitter",
                (10 * z, image.shape[0] - 15 * z),
            )
            cv2.imshow(WINDOW, image)

            key = cv2.waitKey(15) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == 9:
                state["current"] = (index + 1) % len(cameras)
                state["drag"] = None
            elif key == ord("r"):
                placed.clear()
            elif key == ord("a") and frame is not None:
                start = board_to_image(placed) if len(placed) == 4 else None
                result = detect(color_labels(frame), start, tops[index])
                if result is None:
                    print(
                        f"{camera.name} : cible non trouvée. Placer les 4 points à peu près"
                        " (bord extérieur du double), puis A pour les recaler"
                    )
                else:
                    found, error, kept = result
                    placed[:] = [
                        (float(x), float(y))
                        for x, y in project(found, list(CALIBRATION_POINTS))
                    ]
                    print(
                        f"{camera.name} : cible détectée, écart moyen {error:.2f} mm"
                        f" sur {kept} points"
                    )
            elif key == ord("p"):
                captures = data_dir / "captures"
                captures.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                for i, c in enumerate(cameras):
                    photo = captures / f"cam{i + 1}_{stamp}.jpg"
                    # cv2.imwrite échoue sans erreur, par exemple sur un chemin accentué
                    if c.frame is not None and not cv2.imwrite(str(photo), c.frame):
                        print(f"Échec de l'enregistrement : {photo}")
                print(f"Photos enregistrées dans {captures}")
            elif key == ord("s"):
                data_dir.mkdir(parents=True, exist_ok=True)
                # Taille réelle de chaque image : celle à laquelle se rapportent les points
                saved = {
                    "cameras": [
                        {
                            "source": c.source,
                            "width": None if c.frame is None else c.frame.shape[1],
                            "height": None if c.frame is None else c.frame.shape[0],
                            "points": [list(p) for p in pts],
                        }
                        for c, pts in zip(cameras, points)
                    ],
                }
                path.write_text(json.dumps(saved, indent=2), encoding="utf-8")
                print(f"Calibration enregistrée dans {path}")
    finally:
        for camera in cameras:
            camera.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
