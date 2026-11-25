"""Menu principal, historique des parties, profil et calibration."""

import pygame

from ...game.x01 import Turn
from ...storage import history
from .. import theme
from ..buttons import Action
from .base import Item, MenuScreen, Screen


def main_menu(app) -> MenuScreen:
    from .play import opponent_screen

    items = [
        Item("Nouvelle partie", lambda: app.show(opponent_screen(app))),
        Item("Mes parties", lambda: app.show(history_screen(app))),
        Item("Profil", lambda: app.show(ProfileScreen(app))),
        Item("Calibration des caméras", lambda: app.show(CalibrationScreen(app))),
        Item("Se déconnecter", app.log_out),
    ]
    return MenuScreen(app, f"Bonjour {app.user.pseudo}", items)


def describe(game: history.GameSummary) -> tuple[str, str]:
    """Libellé et détail d'une partie dans la liste de l'historique."""
    opponents = " vs ".join(game.players) if len(game.players) > 1 else f"{game.players[0]} en solo"
    if game.status == "abandonnée":
        result = "Abandonnée"
    else:
        result = f"Gagnée par {game.winner}" if len(game.players) > 1 else "Terminée"
    return opponents, f"{game.played_at[:16]}  ·  {result}"


def history_screen(app) -> MenuScreen:
    back = lambda: app.show(main_menu(app))
    games = history.list_games(app.db, app.user.id)
    items = []
    for game in games:
        label, detail = describe(game)
        items.append(Item(label, lambda g=game: app.show(GameDetailScreen(app, g)), detail))
    items.append(Item("Retour", back))
    subtitle = f"{len(games)} partie(s)" if games else "Aucune partie jouée pour l'instant"
    return MenuScreen(app, "Mes parties", items, subtitle=subtitle, on_back=back)


class GameDetailScreen(Screen):
    """Détail des volées d'une partie, par pages. Gauche / Droite : changer de page."""

    rows_per_page = 9

    def __init__(self, app, game: history.GameSummary):
        super().__init__(app)
        self.game = game
        self.turns = history.game_turns(app.db, game.id)
        self.page = 0
        self.pages = max(1, -(-len(self.turns) // self.rows_per_page))

    def handle(self, action: Action) -> None:
        if action is Action.LEFT:
            self.page = max(0, self.page - 1)
        elif action is Action.RIGHT:
            self.page = min(self.pages - 1, self.page + 1)
        else:
            self.app.show(history_screen(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        label, detail = describe(self.game)
        mode = "double out" if self.game.double_out else "sortie simple"
        theme.header(surface, label, f"{self.game.start_score} {mode}  ·  {detail}")
        columns = [("Joueur", 160), ("Volée", 560), ("Fléchettes", 760), ("Total", 1300), ("Reste", 1540)]
        for title, x in columns:
            theme.text(surface, title, 28, (x, 220), theme.MUTED, bold=True)
        start = self.page * self.rows_per_page
        y = 270
        for pseudo, turn in self.turns[start:start + self.rows_per_page]:
            self._row(surface, y, pseudo, turn, columns)
            y += 78
        if not self.turns:
            theme.text(surface, "Aucune fléchette lancée", 36, (theme.WIDTH // 2, 400),
                       theme.MUTED, anchor="midtop")
        theme.footer(surface, f"Page {self.page + 1}/{self.pages}  ·  Gauche / Droite : changer de page"
                              "  ·  appui court : retour")

    def _row(self, surface, y: int, pseudo: str, turn: Turn, columns) -> None:
        rect = pygame.Rect(120, y, theme.WIDTH - 240, 66)
        theme.card(surface, rect)
        darts = "   ".join(d.label for d in turn.darts)
        values = [pseudo, str(turn.number), darts,
                  "BUST" if turn.bust else str(turn.points), str(turn.score_after)]
        for (_, x), value in zip(columns, values):
            color = theme.PINK if value == "BUST" else theme.WHITE
            theme.text(surface, value, 32, (x, rect.centery), color, bold=True, anchor="midleft")


class ProfileScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.stats = history.user_stats(app.db, app.user.id)

    def handle(self, action: Action) -> None:
        if action not in (Action.LEFT, Action.RIGHT):
            self.app.show(main_menu(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        theme.header(surface, self.app.user.pseudo, "Profil  ·  parties terminées")
        s = self.stats
        wins = f"{s.wins}/{s.duels}" if s.duels else "—"
        rate = f"{round(100 * s.wins / s.duels)} %" if s.duels else ""
        tiles = [
            ("Parties jouées", str(s.played), ""),
            ("Victoires à 2", wins, rate),
            ("Moyenne par volée", f"{s.average:g}".replace(".", ","), "points"),
            ("Meilleure volée", str(s.best_turn), "points"),
        ]
        width, gap = 380, 30
        left = (theme.WIDTH - 4 * width - 3 * gap) // 2
        for i, (title, value, unit) in enumerate(tiles):
            rect = pygame.Rect(left + i * (width + gap), 320, width, 320)
            theme.card(surface, rect, border=theme.VIOLET_LIGHT)
            theme.text(surface, title, 30, (rect.centerx, rect.y + 40), theme.MUTED, anchor="midtop")
            theme.text(surface, value, 110, (rect.centerx, rect.centery + 10), theme.ORANGE,
                       bold=True, anchor="center")
            if unit:
                theme.text(surface, unit, 28, (rect.centerx, rect.bottom - 40), theme.MUTED,
                           anchor="midbottom")
        theme.footer(surface, "Appui court : retour")


class CalibrationScreen(Screen):
    """Maquette : la calibration des caméras n'est pas encore développée."""

    cameras = ["Caméra gauche", "Caméra haut", "Caméra droite"]

    def handle(self, action: Action) -> None:
        if action not in (Action.LEFT, Action.RIGHT):
            self.app.show(main_menu(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        theme.header(surface, "Calibration des caméras", "Maquette  ·  fonction à venir")
        width, gap = 540, 30
        left = (theme.WIDTH - 3 * width - 2 * gap) // 2
        for i, name in enumerate(self.cameras):
            rect = pygame.Rect(left + i * (width + gap), 240, width, 560)
            theme.card(surface, rect, border=theme.VIOLET_LIGHT)
            theme.text(surface, name, 36, (rect.centerx, rect.y + 30), bold=True, anchor="midtop")
            preview = pygame.Rect(rect.x + 30, rect.y + 100, width - 60, (width - 60) * 9 // 16)
            pygame.draw.rect(surface, theme.VIOLET, preview, border_radius=12)
            theme.text(surface, "Aperçu indisponible", 28, preview.center, theme.MUTED, anchor="center")
            theme.text(surface, "Statut : non calibrée", 30, (rect.centerx, preview.bottom + 50),
                       theme.PINK, anchor="midtop")
            theme.text(surface, "Distorsion, position", 26, (rect.centerx, preview.bottom + 110),
                       theme.MUTED, anchor="midtop")
            theme.text(surface, "et repères de la cible", 26, (rect.centerx, preview.bottom + 145),
                       theme.MUTED, anchor="midtop")
        theme.footer(surface, "Appui court : retour")
