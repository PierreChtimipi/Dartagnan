import numpy as np

from dartagnan.detection.trigger import ImpactTrigger, motion, small_gray


def run(trigger: ImpactTrigger, amounts: list[float]) -> list[int]:
    """Indices des images où le déclenchement a lieu."""
    return [i for i, a in enumerate(amounts) if trigger.update(a)]


def test_declenche_une_fois_quand_l_image_redevient_stable():
    calm, move = 0.0, 0.05
    amounts = [calm] * 20 + [move] * 5 + [calm] * 15
    assert run(ImpactTrigger(still_frames=10), amounts) == [34]


def test_rien_sans_mouvement_ni_pendant_le_mouvement():
    assert run(ImpactTrigger(), [0.0] * 50) == []
    assert run(ImpactTrigger(), [0.05] * 50) == []


def test_un_mouvement_qui_reprend_repousse_le_declenchement():
    amounts = [0.05] * 3 + [0.0] * 5 + [0.05] * 3 + [0.0] * 10
    assert run(ImpactTrigger(still_frames=10), amounts) == [20]


def test_bruit_entre_calme_et_mouvement_ne_compte_pas_comme_calme():
    amounts = [0.05] + [0.001] * 30  # ni calme (< 0,0005) ni mouvement (> 0,002)
    assert run(ImpactTrigger(), amounts) == []


def test_mouvement_mesure_seulement_sur_la_cible():
    before = np.full((720, 1280, 3), 100, np.uint8)
    after = before.copy()
    after[:100, :100] = 250  # changement hors de la cible
    after[400:420, 600:620] = 250  # changement sur la cible
    mask = np.zeros((180, 320), np.uint8)
    mask[60:120, 120:200] = 1
    on_board = motion(small_gray(before), small_gray(after), mask)
    assert 0 < on_board < 0.1
    assert motion(small_gray(before), small_gray(before), mask) == 0
