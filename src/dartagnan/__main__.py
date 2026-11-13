"""Point d'entrée : python -m dartagnan

Variable d'environnement DARTAGNAN_DATA : dossier de la base de données
(par défaut /var/lib/dartagnan, créé par system/install.sh sur la Pi).
"""

import os
from pathlib import Path

import pygame

from .display.app import App, is_fullscreen
from .storage import db


def main() -> None:
    data_dir = Path(os.environ.get("DARTAGNAN_DATA", "/var/lib/dartagnan"))
    conn = db.connect(data_dir)
    try:
        App(conn, is_fullscreen()).run()
    finally:
        conn.close()
        pygame.quit()


if __name__ == "__main__":
    main()
