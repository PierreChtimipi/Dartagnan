"""Historique des parties et statistiques des joueurs."""

import sqlite3
from dataclasses import dataclass

from ..game.darts import Dart
from ..game.x01 import Turn, X01Game
from .accounts import User


@dataclass(frozen=True)
class GameSummary:
    id: int
    played_at: str
    start_score: int
    double_out: bool
    status: str
    players: list[str]
    winner: str | None


@dataclass(frozen=True)
class Stats:
    played: int        # parties finies
    duels: int         # parties finies à plusieurs joueurs
    wins: int          # victoires dans ces duels
    average: float     # points moyens par volée, bust compté 0
    best_turn: int     # meilleure volée


def save_game(conn: sqlite3.Connection, game: X01Game, players: list[User]) -> int:
    """Enregistre une partie (finie ou abandonnée) avec toutes ses volées."""
    winner_id = players[game.winner].id if game.is_over else None
    with conn:
        cur = conn.execute(
            "INSERT INTO games (start_score, double_out, status, winner_id) VALUES (?, ?, ?, ?)",
            (game.start, int(game.double_out), "finie" if game.is_over else "abandonnée", winner_id),
        )
        game_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO game_players (game_id, user_id, position) VALUES (?, ?, ?)",
            [(game_id, user.id, i) for i, user in enumerate(players)],
        )
        for turn in game.played_turns:
            cur = conn.execute(
                "INSERT INTO turns (game_id, user_id, number, score_before, points, bust)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (game_id, players[turn.player].id, turn.number, turn.score_before,
                 turn.points, int(turn.bust)),
            )
            conn.executemany(
                "INSERT INTO darts (turn_id, position, segment, multiplier) VALUES (?, ?, ?, ?)",
                [(cur.lastrowid, i, d.segment, d.multiplier) for i, d in enumerate(turn.darts)],
            )
    return game_id


def list_games(conn: sqlite3.Connection, user_id: int) -> list[GameSummary]:
    """Parties d'un joueur, de la plus récente à la plus ancienne."""
    rows = conn.execute(
        """SELECT g.*, w.pseudo AS winner_pseudo FROM games g
           JOIN game_players gp ON gp.game_id = g.id AND gp.user_id = ?
           LEFT JOIN users w ON w.id = g.winner_id
           ORDER BY g.id DESC""",
        (user_id,),
    ).fetchall()
    return [
        GameSummary(r["id"], r["played_at"], r["start_score"], bool(r["double_out"]), r["status"],
                    _players(conn, r["id"]), r["winner_pseudo"])
        for r in rows
    ]


def _players(conn: sqlite3.Connection, game_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT u.pseudo FROM game_players gp JOIN users u ON u.id = gp.user_id
           WHERE gp.game_id = ? ORDER BY gp.position""",
        (game_id,),
    )
    return [r["pseudo"] for r in rows]


def game_turns(conn: sqlite3.Connection, game_id: int) -> list[tuple[str, Turn]]:
    """Volées d'une partie dans l'ordre de jeu, avec le pseudo du joueur."""
    positions = {
        r["user_id"]: r["position"]
        for r in conn.execute("SELECT user_id, position FROM game_players WHERE game_id = ?", (game_id,))
    }
    rows = conn.execute(
        """SELECT t.*, u.pseudo FROM turns t JOIN users u ON u.id = t.user_id
           WHERE t.game_id = ? ORDER BY t.id""",
        (game_id,),
    ).fetchall()
    result = []
    for r in rows:
        darts = [
            Dart(d["segment"], d["multiplier"])
            for d in conn.execute(
                "SELECT segment, multiplier FROM darts WHERE turn_id = ? ORDER BY position", (r["id"],)
            )
        ]
        turn = Turn(positions[r["user_id"]], r["number"], r["score_before"], darts, bool(r["bust"]))
        result.append((r["pseudo"], turn))
    return result


def user_stats(conn: sqlite3.Connection, user_id: int) -> Stats:
    games = conn.execute(
        """SELECT COUNT(*) AS played,
                  COALESCE(SUM((SELECT COUNT(*) FROM game_players p WHERE p.game_id = g.id) > 1), 0) AS duels,
                  COALESCE(SUM(g.winner_id = ? AND
                      (SELECT COUNT(*) FROM game_players p WHERE p.game_id = g.id) > 1), 0) AS wins
           FROM games g JOIN game_players gp ON gp.game_id = g.id AND gp.user_id = ?
           WHERE g.status = 'finie'""",
        (user_id, user_id),
    ).fetchone()
    turns = conn.execute(
        """SELECT AVG(t.points) AS average, MAX(t.points) AS best FROM turns t
           JOIN games g ON g.id = t.game_id
           WHERE t.user_id = ? AND g.status = 'finie'""",
        (user_id,),
    ).fetchone()
    return Stats(games["played"], games["duels"], games["wins"],
                 round(turns["average"] or 0, 1), turns["best"] or 0)
