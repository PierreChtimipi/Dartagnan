"""Détection sur des séries de photos réelles, comparée aux zones réelles.

Une série est un dossier contenant, pour chaque caméra, les photos camN_<horodatage>.jpg
prises avec la touche P de calibrate_board.py : cible vide, puis une fléchette de plus à
chaque photo. points.txt donne la zone réelle de chaque fléchette, une par ligne, dans
l'ordre (20, T19, D5, 25, Bull, Out).

Pour chaque série : calibration automatique de chaque caméra sur sa photo vide, axe de
chaque nouvelle fléchette par différence d'images limitée à la cible, droites projetées
sur la cible, intersection, zone. Résultats dans le terminal et dans --out.

    $env:PYTHONPATH="src"
    .venv\\Scripts\\python tools\\detect_photos.py photos\\2026-11-19-serie1 photos\\2026-11-19-serie2
"""

import argparse
import glob
from pathlib import Path

import cv2
import numpy as np
from calibrate_board import draw_board

from dartagnan.detection.dart import board_mask, dart_line
from dartagnan.game.darts import Dart
from dartagnan.geometry.auto_calibration import color_labels, detect
from dartagnan.geometry.board import dart_at
from dartagnan.geometry.triangulation import board_line, intersect

COLORS = ((255, 0, 255), (255, 255, 0), (0, 255, 255))  # une couleur par caméra
SCALE, HALF = 2.0, 230.0  # vue de face : px par mm, mm affichés autour du centre
SIZE = round(2 * HALF * SCALE)
FRONT_TO_BOARD = np.array([[1 / SCALE, 0, -HALF], [0, -1 / SCALE, HALF], [0, 0, 1]])


def label(
    image: np.ndarray, text: str, org: tuple[int, int], color: tuple = (255, 255, 255)
) -> None:
    # Polices Hershey d'OpenCV : pas d'accents dans les textes affichés
    cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 5)
    cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)


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


def same_zone(truth: str, dart: Dart | None) -> bool:
    """Zone réelle de points.txt (20, T19, D5, 25, Bull, Out) et fléchette détectée."""
    if dart is None:
        return False
    truth = truth.strip().lower()
    if truth in ("out", "raté", "rate", "hors cible"):
        return dart.segment == 0
    if truth in ("bull", "50", "d25"):
        return dart.label == "Bull"
    return truth == dart.label.lower()


def run_series(
    folder: Path, tops: list[float], out: Path
) -> list[tuple[str, Dart | None, float | None]]:
    """Détection sur une série : (zone réelle, fléchette détectée, écart entre les
    droites en mm) pour chaque fléchette, images dans `out`."""
    cameras = len(tops)
    shots = [
        [cv2.imread(p) for p in sorted(glob.glob(str(folder / f"cam{i + 1}_*.jpg")))]
        for i in range(cameras)
    ]
    counts = {len(s) for s in shots}
    if len(counts) != 1 or 0 in counts:
        raise SystemExit(
            f"{folder} : nombre de photos différent selon les caméras {counts}"
        )
    lines_of_file = (folder / "points.txt").read_text(encoding="utf-8").splitlines()
    truth = [z.strip() for z in lines_of_file if z.strip()]

    homographies, grids = [], []
    for i in range(cameras):
        result = detect(color_labels(shots[i][0]), top=tops[i])
        if result is None:
            print(
                f"{folder.name} caméra {i + 1} : calibration impossible, série ignorée"
            )
            return []
        homographies.append(result[0])
        grid = shots[i][0].copy()
        draw_board(grid, result[0])
        label(grid, f"camera {i + 1} : ecart {result[1]:.2f} mm", (20, 40))
        grids.append(cv2.resize(grid, (640, 360)))
    cv2.imwrite(str(out / f"{folder.name}_calibration.png"), np.hstack(grids))

    masks = [board_mask(homographies[i], shots[i][0].shape) for i in range(cameras)]
    front = cv2.warpPerspective(
        shots[0][-1],
        homographies[0] @ FRONT_TO_BOARD,
        (SIZE, SIZE),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
    )
    results = []
    for k in range(1, len(shots[0])):
        lines, views = [], []
        for i in range(cameras):
            image_line = dart_line(shots[i][k - 1], shots[i][k], masks[i])
            view = shots[i][k].copy()
            label(view, f"camera {i + 1}", (20, 40))
            if image_line is not None:
                lines.append(board_line(homographies[i], image_line))
                ends = line_ends(image_line, view.shape[1], view.shape[0])
                if len(ends) == 2:
                    cv2.line(view, ends[0], ends[1], (0, 0, 255), 2)
                a, b, c = lines[-1]
                front_line = np.array([a / SCALE, -b / SCALE, c - a * HALF + b * HALF])
                ends = line_ends(front_line, SIZE, SIZE)
                if len(ends) == 2:
                    cv2.line(front, ends[0], ends[1], COLORS[i % 3], 1, cv2.LINE_AA)
            views.append(cv2.resize(view, (640, 360)))
        cv2.imwrite(str(out / f"{folder.name}_flechette{k}_axes.png"), np.hstack(views))
        real = truth[k - 1] if k - 1 < len(truth) else "?"
        found = intersect(lines)
        if found is None:
            results.append((real, None, None))
            continue
        point, spread = found
        dart = dart_at(*point)
        results.append((real, dart, spread))
        x, y = round((point[0] + HALF) * SCALE), round((HALF - point[1]) * SCALE)
        color = (0, 200, 0) if same_zone(real, dart) else (0, 0, 255)
        cv2.drawMarker(front, (x, y), color, cv2.MARKER_CROSS, 20, 3)
        label(front, f"{k}: {dart.label} (reel {real})", (x + 12, y - 12), color)
    label(front, f"{folder.name} : vue de face (camera 1 redressee)", (20, 40))
    cv2.imwrite(str(out / f"{folder.name}_vue_de_face.png"), front)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("series", nargs="+", type=Path, help="dossiers de séries")
    parser.add_argument(
        "--top",
        type=float,
        nargs="+",
        default=[180.0, 54.0, 306.0],
        help="angle de la cible en haut de l'image, par caméra (défaut : 20, 16, 15)",
    )
    parser.add_argument("--out", type=Path, default=Path("data/detection"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows = [
        "| Série | Fléchette | Réel | Détecté | Juste | Écart entre droites |",
        "|---|---|---|---|---|---|",
    ]
    right = total = 0
    for folder in args.series:
        for k, (real, dart, spread) in enumerate(
            run_series(folder, args.top, args.out), 1
        ):
            ok = same_zone(real, dart)
            right += ok
            total += 1
            found = "non détectée" if dart is None else dart.label
            gap = "" if spread is None else f"{spread:.1f} mm"
            rows.append(
                f"| {folder.name} | {k} | {real} | {found} | {'oui' if ok else 'non'} | {gap} |"
            )
    rows.append(f"\n{right}/{total} zones justes")
    report = "\n".join(rows)
    (args.out / "resultats.md").write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"Images et tableau : {args.out}")


if __name__ == "__main__":
    main()
