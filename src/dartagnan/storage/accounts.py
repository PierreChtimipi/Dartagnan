"""Comptes joueurs : pseudo et code PIN.

Le PIN n'est jamais stocké en clair : seul son empreinte scrypt (avec un sel
aléatoire par compte) est enregistrée. Après plusieurs codes faux, le compte est
bloqué quelques minutes pour empêcher d'essayer tous les codes.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass

PSEUDO_RE = re.compile(r"[A-Za-z0-9_-]{3,16}")
PIN_RE = re.compile(r"[0-9]{4,6}")
MAX_ATTEMPTS = 5
LOCK_SECONDS = 5 * 60

# Paramètres scrypt : environ 16 Mo de mémoire, raisonnable sur une Pi 4
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


class AccountError(Exception):
    """Erreur affichable telle quelle à l'utilisateur."""


@dataclass(frozen=True)
class User:
    id: int
    pseudo: str


def _hash_pin(pin: str, salt: bytes) -> bytes:
    return hashlib.scrypt(pin.encode(), salt=salt, **_SCRYPT)


def validate_pseudo(pseudo: str) -> None:
    if not PSEUDO_RE.fullmatch(pseudo):
        raise AccountError("Pseudo : 3 à 16 caractères, lettres, chiffres, - ou _")


def validate_pin(pin: str) -> None:
    if not PIN_RE.fullmatch(pin):
        raise AccountError("Code : 4 à 6 chiffres")


def create_account(conn: sqlite3.Connection, pseudo: str, pin: str) -> User:
    validate_pseudo(pseudo)
    validate_pin(pin)
    salt = secrets.token_bytes(16)
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (pseudo, pin_hash, pin_salt) VALUES (?, ?, ?)",
                (pseudo, _hash_pin(pin, salt), salt),
            )
    except sqlite3.IntegrityError:
        raise AccountError("Ce pseudo est déjà pris") from None
    return User(cur.lastrowid, pseudo)


def pseudo_exists(conn: sqlite3.Connection, pseudo: str) -> bool:
    return conn.execute("SELECT 1 FROM users WHERE pseudo = ?", (pseudo,)).fetchone() is not None


def list_users(conn: sqlite3.Connection) -> list[User]:
    rows = conn.execute("SELECT id, pseudo FROM users ORDER BY pseudo COLLATE NOCASE")
    return [User(r["id"], r["pseudo"]) for r in rows]


def login(conn: sqlite3.Connection, user_id: int, pin: str, now: float | None = None) -> User:
    """Vérifie le code PIN. Lève AccountError si le code est faux ou le compte bloqué."""
    now = time.time() if now is None else now
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise AccountError("Compte introuvable")
    if row["locked_until"] > now:
        minutes = int((row["locked_until"] - now) // 60) + 1
        raise AccountError(f"Trop d'essais : compte bloqué {minutes} min")

    # Le calcul est fait même si le format est faux, pour un temps de réponse constant
    ok = hmac.compare_digest(_hash_pin(pin, row["pin_salt"]), row["pin_hash"])
    with conn:
        if ok:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = 0 WHERE id = ?", (user_id,)
            )
            return User(row["id"], row["pseudo"])
        attempts = row["failed_attempts"] + 1
        if attempts >= MAX_ATTEMPTS:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE id = ?",
                (now + LOCK_SECONDS, user_id),
            )
        else:
            conn.execute("UPDATE users SET failed_attempts = ? WHERE id = ?", (attempts, user_id))
    if attempts >= MAX_ATTEMPTS:
        raise AccountError(f"Trop d'essais : compte bloqué {LOCK_SECONDS // 60} min")
    raise AccountError(f"Code incorrect ({MAX_ATTEMPTS - attempts} essai(s) restant(s))")
