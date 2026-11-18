"""Tests sur vues de synthèse des caméras virtuelles (`synthetic.py`)."""

import math

import numpy as np
import pytest
import synthetic
from synthetic import SimulatedCamera

from dartagnan.detection.dart import dart_line
from dartagnan.game.darts import Dart
from dartagnan.geometry.auto_calibration import color_labels, detect
from dartagnan.geometry.board import board_point, dart_at
from dartagnan.geometry.calibration import image_to_board, project
from dartagnan.geometry.triangulation import board_line, intersect


def test_calibration_auto_en_vue_rasante_d_une_camera_au_droit_du_16():
    camera = SimulatedCamera.around_board(16)
    # Caméra au-dessus du 16 (234°) : le côté opposé (54°) est en haut de l'image
    found, _, _ = detect(color_labels(synthetic.render_board(camera)), top=54)
    checks = [board_point(a, r) for a in range(0, 360, 30) for r in (0, 103, 166)]
    error = max(
        math.dist(image_to_board(found, tuple(project(camera.homography, [p])[0])), p)
        for p in checks
    )
    assert error < 1.0


def test_axe_projete_passe_par_la_pointe():
    camera = SimulatedCamera.around_board(20)
    tip = np.array([40.0, -70.0, 0.0])
    axis = np.array([0.2, 0.3, 0.93])
    pixels, _ = camera.project(np.array([tip + 30 * axis, tip + 120 * axis]))
    image_line = np.cross([*pixels[0], 1.0], [*pixels[1], 1.0])
    line = board_line(camera.homography, image_line)
    assert line @ [40.0, -70.0, 1.0] == pytest.approx(0, abs=1e-6)


def test_volee_vue_par_les_trois_cameras():
    rng = np.random.default_rng(0)
    cameras = [SimulatedCamera.around_board(s) for s in synthetic.CAMERA_SECTORS]
    scenes = [synthetic.render_board(c) for c in cameras]
    before = [synthetic.noisy(s, rng) for s in scenes]
    throws = [
        ((0.0, 103.0), Dart(20, 3)),
        ((-60.0, -45.0), Dart(16, 1)),
        ((120.0, -50.0), Dart(10, 1)),
    ]
    for tip, expected in throws:
        lines = []
        for i, camera in enumerate(cameras):
            synthetic.draw_dart(scenes[i], camera, tip, np.array([0.1, 0.3, 0.95]))
            after = synthetic.noisy(scenes[i], rng)
            lines.append(board_line(camera.homography, dart_line(before[i], after)))
            before[i] = after
        point, _ = intersect(lines)
        assert math.dist(point, tip) < 2.0
        assert dart_at(*point) == expected
