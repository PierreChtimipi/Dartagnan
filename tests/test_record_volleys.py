import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from record_volleys import parse_zones, volley_folder


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
