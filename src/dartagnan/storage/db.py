"""Base SQLite : ouverture et création du schéma.

Toutes les requêtes passent des paramètres (`?`), jamais de texte concaténé.
"""

import os
import sqlite3
from pathlib import Path

DB_NAME = "dartagnan.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,
    pseudo          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pin_hash        BLOB NOT NULL,
    pin_salt        BLOB NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    REAL NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS games (
    id          INTEGER PRIMARY KEY,
    start_score INTEGER NOT NULL,
    double_out  INTEGER NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('finie', 'abandonnée')),
    winner_id   INTEGER REFERENCES users(id),
    played_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS game_players (
    game_id  INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id  INTEGER NOT NULL REFERENCES users(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (game_id, position)
);

CREATE TABLE IF NOT EXISTS turns (
    id           INTEGER PRIMARY KEY,
    game_id      INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    number       INTEGER NOT NULL,
    score_before INTEGER NOT NULL,
    points       INTEGER NOT NULL,
    bust         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS darts (
    turn_id    INTEGER NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    segment    INTEGER NOT NULL,
    multiplier INTEGER NOT NULL,
    PRIMARY KEY (turn_id, position)
);
"""


def connect(data_dir: Path) -> sqlite3.Connection:
    """Ouvre (et crée si besoin) la base, lisible uniquement par l'utilisateur du jeu."""
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = data_dir / DB_NAME
    path.touch(mode=0o600, exist_ok=True)
    os.chmod(path, 0o600)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def connect_memory() -> sqlite3.Connection:
    """Base en mémoire, pour les tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
