import pytest

from dartagnan.game.darts import Dart
from dartagnan.game.x01 import X01Game
from dartagnan.storage import accounts, db, history


@pytest.fixture
def conn():
    return db.connect_memory()


def test_compte_et_connexion(conn):
    user = accounts.create_account(conn, "Sacha_B", "1234")
    assert accounts.login(conn, user.id, "1234") == user
    row = conn.execute("SELECT pin_hash FROM users").fetchone()
    assert b"1234" not in row["pin_hash"]


def test_pseudo_unique_sans_casse(conn):
    accounts.create_account(conn, "Sacha", "1234")
    with pytest.raises(accounts.AccountError):
        accounts.create_account(conn, "sacha", "9999")


@pytest.mark.parametrize("pseudo, pin", [("ab", "1234"), ("a b c", "1234"), ("x' OR 1=1", "1234"),
                                         ("Sacha", "123"), ("Sacha", "12a4"), ("Sacha", "1234567")])
def test_saisies_invalides(conn, pseudo, pin):
    with pytest.raises(accounts.AccountError):
        accounts.create_account(conn, pseudo, pin)


def test_blocage_apres_trop_d_essais(conn):
    user = accounts.create_account(conn, "Sacha", "1234")
    for _ in range(accounts.MAX_ATTEMPTS):
        with pytest.raises(accounts.AccountError):
            accounts.login(conn, user.id, "0000", now=1000)
    with pytest.raises(accounts.AccountError, match="bloqué"):
        accounts.login(conn, user.id, "1234", now=1001)
    assert accounts.login(conn, user.id, "1234", now=1000 + accounts.LOCK_SECONDS + 1) == user


def test_historique_et_statistiques(conn):
    a = accounts.create_account(conn, "Alice", "1111")
    b = accounts.create_account(conn, "Bob", "2222")
    game = X01Game(2)
    for dart in [Dart(20, 1)] * 3 + [Dart(1, 1)] * 3:
        game.throw(dart)
    history.save_game(conn, game, [a, b])  # abandonnée
    game = X01Game(2, start=70)
    for dart in [Dart(20, 3), Dart(20, 1), Dart(1, 1), Dart(1, 1), Dart(1, 1), Dart(20, 3), Dart(10, 1)]:
        game.throw(dart)
    history.save_game(conn, game, [a, b])  # Alice : bust (80), Bob : 3, Alice gagne (70)

    games = history.list_games(conn, a.id)
    assert [g.status for g in games] == ["finie", "abandonnée"]
    assert games[0].winner == "Alice" and games[0].players == ["Alice", "Bob"]

    turns = history.game_turns(conn, games[0].id)
    assert [(p, t.bust, t.points) for p, t in turns] == [
        ("Alice", True, 0), ("Bob", False, 3), ("Alice", False, 70)]
    assert [d.label for d in turns[0][1].darts] == ["T20", "20"]

    stats = history.user_stats(conn, a.id)
    assert (stats.played, stats.duels, stats.wins, stats.average, stats.best_turn) == (1, 1, 1, 35.0, 70)
    assert history.user_stats(conn, b.id).wins == 0
