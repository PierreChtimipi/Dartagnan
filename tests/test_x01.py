import pytest

from dartagnan.game.darts import BULL, MISS, Dart
from dartagnan.game.x01 import X01Game


def throw(game, *darts):
    for segment, multiplier in darts:
        game.throw(Dart(segment, multiplier))


def test_volee_soustrait_et_passe_au_joueur_suivant():
    game = X01Game(2)
    throw(game, (20, 3), (20, 1), (5, 2))
    assert game.scores == [301 - 90, 301]
    assert game.current_player == 1


def test_solo_reste_sur_le_meme_joueur():
    game = X01Game(1)
    throw(game, (1, 1), (1, 1), (1, 1))
    assert game.current_player == 0
    assert game.current_turn.number == 2


def test_bust_revient_au_score_du_debut_de_volee():
    game = X01Game(2, start=40)
    throw(game, (20, 1), (20, 2))
    assert game.turns[0].bust
    assert game.scores[0] == 40
    assert game.current_player == 1


def test_victoire_sortie_simple():
    game = X01Game(2, start=40)
    throw(game, (20, 1), (10, 1), (10, 1))
    assert game.winner == 0
    with pytest.raises(RuntimeError):
        game.throw(Dart(1, 1))


def test_double_out_exige_un_double():
    game = X01Game(1, start=40, double_out=True)
    throw(game, (20, 1), (20, 1))
    assert game.turns[0].bust and game.winner is None
    throw(game, (20, 2))
    assert game.winner == 0


def test_double_out_reste_a_un_est_un_bust():
    game = X01Game(1, start=41, double_out=True)
    throw(game, (20, 2))
    assert game.turns[0].bust


def test_bull_compte_comme_double():
    game = X01Game(1, start=50, double_out=True)
    throw(game, (BULL, 2))
    assert game.winner == 0


def test_annuler_traverse_les_volees_et_la_victoire():
    game = X01Game(2, start=40)
    throw(game, (1, 1), (1, 1), (1, 1), (20, 2))
    assert game.winner == 1
    assert game.undo() == Dart(20, 2)
    assert game.winner is None and game.current_player == 1
    game.undo()
    assert game.current_player == 0 and len(game.current_turn.darts) == 2
    assert game.turn_in_progress_score() == 38


def test_annuler_sans_fleche():
    assert X01Game(1).undo() is None


@pytest.mark.parametrize("segment, multiplier", [(0, 2), (25, 3), (21, 1), (5, 4)])
def test_flechettes_invalides(segment, multiplier):
    with pytest.raises(ValueError):
        Dart(segment, multiplier)


def test_libelles():
    assert [Dart(20, 3).label, Dart(16, 2).label, Dart(5, 1).label] == ["T20", "D16", "5"]
    assert [Dart(BULL, 1).label, Dart(BULL, 2).label, Dart(MISS, 1).label] == ["25", "Bull", "Raté"]
