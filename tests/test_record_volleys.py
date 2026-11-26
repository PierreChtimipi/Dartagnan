import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
import record_volleys
from record_volleys import Recorder, manual_points, parse_zones, volley_folder


def test_zones_tapees_au_format_de_points_txt():
    assert parse_zones("20 t19, d5") == ["20", "T19", "D5"]
    assert parse_zones("bull 25 out raté 50") == ["Bull", "25", "Out", "Out", "Bull"]
    assert parse_zones("") == []


def test_zone_invalide_refusee():
    for text in ("T21", "2O", "vdie", "T25", "20 0"):
        assert parse_zones(text) is None


def test_numero_de_volee_a_la_suite_du_plus_grand_du_jour(tmp_path):
    today = time.strftime("%d%m%y")
    (tmp_path / f"{today}-0900-volee1").mkdir()
    (tmp_path / f"{today}-0930-volee3").mkdir()  # volee2 supprimée
    (tmp_path / "010199-1200-volee9").mkdir()  # autre jour
    name = volley_folder(tmp_path).name
    assert name.startswith(today)
    assert name.endswith("-volee4")


def test_points_manuels_de_la_meme_source_et_de_la_meme_taille(tmp_path):
    path = tmp_path / "calibration.json"
    shape = (720, 1280, 3)
    assert manual_points(path, "1", shape) is None  # pas de fichier
    points = [[100, 50], [900, 300], [700, 650], [80, 400]]
    cameras = [
        {"source": "1", "width": 1280, "height": 720, "points": points},
        {"source": "2", "width": 1280, "height": 720, "points": points[:3]},
        {"source": "3", "width": 640, "height": 360, "points": points},
    ]
    path.write_text(json.dumps({"cameras": cameras}), encoding="utf-8")
    assert manual_points(path, "1", shape) == [tuple(p) for p in points]
    assert manual_points(path, "2", shape) is None  # points incomplets
    assert manual_points(path, "3", shape) is None  # autre taille d'image
    assert manual_points(path, "4", shape) is None  # source inconnue


class FakeCamera:
    def __init__(self, frame: np.ndarray) -> None:
        self.frame, self.count, self.source = frame, 0, "1"


def test_photo_sans_flechette_ignoree_et_cible_pas_vide_refusee(tmp_path, monkeypatch):
    monkeypatch.setattr(record_volleys, "board_surface", lambda: None)  # sans police
    empty = np.full((360, 640, 3), 200, np.uint8)
    dart = empty.copy()
    cv2.line(dart, (300, 100), (340, 250), (0, 0, 0), 6)
    cameras = [FakeCamera(empty) for _ in range(3)]
    recorder = Recorder(cameras, [0.0] * 3, tmp_path)
    recorder.homographies = [np.eye(3)] * 3
    recorder.masks = [np.ones(empty.shape[:2], np.uint8)] * 3
    recorder.open_volley([empty] * 3)
    first = recorder.folder

    recorder.capture([empty] * 3)  # déclenchement sans nouvelle fléchette
    assert recorder.shots == []
    assert len(list(first.iterdir())) == 3  # photos de la cible vide seulement
    recorder.capture([dart] * 3)
    assert len(recorder.shots) == 1

    recorder.typed = "20"
    for camera in cameras:
        camera.frame = dart  # fléchette pas retirée
    recorder.next_volley()
    assert recorder.folder == first
    assert not (first / "points.txt").exists()
    for camera in cameras:
        camera.frame = empty
    recorder.next_volley()
    assert recorder.folder != first
    assert (first / "points.txt").read_text(encoding="utf-8") == "20\n"
