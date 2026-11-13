"""Création d'une partie de 301, saisie des fléchettes et fin de partie."""

import pygame

from ...game.darts import BULL, MISS, Dart
from ...game.x01 import DARTS_PER_TURN, X01Game
from ...storage import accounts, history
from .. import theme
from ..buttons import Action
from .base import Item, MenuScreen, Screen

START_SCORE = 301

# Pavé de saisie : ligne de touches spéciales, puis les secteurs de 20 à 1
UNDO, QUIT = "Annuler", "Quitter"
PAD = ["25", "Bull", "Raté", UNDO, QUIT] + [str(n) for n in range(20, 0, -1)]
PAD_COLUMNS = 5


def opponent_screen(app) -> MenuScreen:
    from .menu import main_menu

    back = lambda: app.show(main_menu(app))
    others = [u for u in accounts.list_users(app.db) if u.id != app.user.id]
    items = [Item("Solo", lambda: app.show(mode_screen(app, [app.user])))]
    items += [Item(f"Contre {u.pseudo}", lambda u=u: app.show(mode_screen(app, [app.user, u])))
              for u in others]
    items.append(Item("Retour", back))
    return MenuScreen(app, "Nouvelle partie · 301", items, subtitle="1 · Contre qui ?", on_back=back)


def mode_screen(app, players: list[accounts.User]) -> MenuScreen:
    def start(double_out: bool):
        app.show(GameScreen(app, players, X01Game(len(players), START_SCORE, double_out)))
        app.toast("Partie lancée !", theme.GREEN)

    items = [
        Item("Sortie simple", lambda: start(False), "finir exactement à 0"),
        Item("Double out", lambda: start(True), "finir à 0 sur un double ou le Bull"),
        Item("Retour", lambda: app.show(opponent_screen(app))),
    ]
    return MenuScreen(app, "Nouvelle partie · 301", items, subtitle="2 · Comment finir ?",
                      on_back=lambda: app.show(opponent_screen(app)))


def dart_for(key: str, action: Action) -> Dart | str:
    """Fléchette correspondant à une touche du pavé et au geste, ou message d'erreur."""
    multiplier = {Action.SINGLE: 1, Action.DOUBLE: 2, Action.TRIPLE: 3}[action]
    if key == "Raté":
        return Dart(MISS, 1)
    if key == "Bull":
        return Dart(BULL, 2)
    if key == "25":
        return "Le triple 25 n'existe pas" if multiplier == 3 else Dart(BULL, multiplier)
    return Dart(int(key), multiplier)


class GameScreen(Screen):
    idle_logout = False  # une partie en cours n'est jamais interrompue

    def __init__(self, app, players: list[accounts.User], game: X01Game, index: int = 5):
        super().__init__(app)
        self.players = players
        self.game = game
        self.index = index  # sur le 20 par défaut

    @property
    def mode(self) -> str:
        return f"{self.game.start}  ·  {'double out' if self.game.double_out else 'sortie simple'}"

    def handle(self, action: Action) -> None:
        if action is Action.LEFT:
            self.index = (self.index - 1) % len(PAD)
            return
        if action is Action.RIGHT:
            self.index = (self.index + 1) % len(PAD)
            return
        key = PAD[self.index]
        if key == UNDO:
            dart = self.game.undo()
            self.app.toast(f"{dart.label} annulée" if dart else "Rien à annuler", theme.TURQUOISE)
        elif key == QUIT:
            self.app.show(quit_screen(self.app, self))
        else:
            dart = dart_for(key, action)
            if isinstance(dart, str):
                self.app.toast(dart, theme.PINK)
            else:
                self.throw(dart)

    def throw(self, dart: Dart) -> None:
        turns_before = len(self.game.turns)
        self.game.throw(dart)
        if self.game.is_over:
            self.app.show(GameOverScreen(self.app, self))
        elif len(self.game.turns) > turns_before and self.game.turns[-2].bust:
            self.app.toast("BUST !  Le score revient au début de la volée", theme.PINK)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(theme.logo(60), (40, 24))
        theme.text(surface, self.mode, 34, (theme.WIDTH // 2, 40), theme.MUTED, bold=True,
                   anchor="midtop")
        self._draw_players(surface)
        self._draw_turn(surface)
        self._draw_pad(surface)
        theme.footer(surface, "Gauche / Droite : choisir  ·  appui court : simple  ·  "
                              "deux appuis : double  ·  appui long : triple")

    def _draw_players(self, surface: pygame.Surface) -> None:
        count = len(self.players)
        gap = 40
        width = (theme.WIDTH - 80 - gap * (count - 1)) // count
        for i, user in enumerate(self.players):
            rect = pygame.Rect(40 + i * (width + gap), 100, width, 210)
            active = i == self.game.current_player
            theme.card(surface, rect, selected=active)
            score = self.game.turn_in_progress_score() if active else self.game.scores[i]
            theme.text(surface, user.pseudo, 36, (rect.x + 36, rect.y + 16), bold=True)
            theme.text(surface, str(score), 124, (rect.x + 36, rect.bottom + 8),
                       theme.ORANGE if active else theme.WHITE, bold=True, anchor="bottomleft")
            # Moyenne sur les volées terminées de ce joueur
            turns = [t for t in self.game.turns
                     if t.player == i and (t.bust or len(t.darts) == DARTS_PER_TURN)]
            average = sum(t.points for t in turns) / len(turns) if turns else 0
            theme.text(surface, f"Moyenne {average:.1f}".replace(".", ","), 30,
                       (rect.right - 36, rect.y + 20), theme.MUTED, anchor="topright")

    def _draw_turn(self, surface: pygame.Surface) -> None:
        turn = self.game.current_turn
        player = self.players[turn.player].pseudo
        theme.text(surface, f"Volée {turn.number} de {player}", 32, (40, 365), theme.MUTED,
                   bold=True, anchor="midleft")
        for i in range(DARTS_PER_TURN):
            rect = pygame.Rect(480 + i * 200, 330, 180, 70)
            theme.card(surface, rect, border=theme.VIOLET_LIGHT)
            if i < len(turn.darts):
                theme.text(surface, turn.darts[i].label, 38, rect.center, bold=True, anchor="center")
        total = sum(d.points for d in turn.darts)
        theme.text(surface, f"= {total}", 40, (1100, 365), bold=True, anchor="midleft")

    def _draw_pad(self, surface: pygame.Surface) -> None:
        gap = 12
        width = (theme.WIDTH - 80 - gap * (PAD_COLUMNS - 1)) // PAD_COLUMNS
        height = 104
        colors = {"25": theme.TEAL, "Bull": theme.TEAL, "Raté": theme.VIOLET_DARK,
                  UNDO: theme.VIOLET_LIGHT, QUIT: theme.VIOLET_LIGHT}
        for i, key in enumerate(PAD):
            row, col = divmod(i, PAD_COLUMNS)
            rect = pygame.Rect(40 + col * (width + gap), 424 + row * (height + gap), width, height)
            theme.card(surface, rect, selected=(i == self.index), fill=colors.get(key, theme.VIOLET_DARK))
            theme.text(surface, key, 52 if key.isdigit() else 40, rect.center, bold=True,
                       anchor="center")


def quit_screen(app, game_screen: GameScreen) -> MenuScreen:
    from .menu import main_menu

    def abandon():
        if game_screen.game.played_turns:
            history.save_game(app.db, game_screen.game, game_screen.players)
        app.show(main_menu(app))

    resume = lambda: app.show(game_screen)
    items = [
        Item("Reprendre la partie", resume),
        Item("Abandonner", abandon, "la partie est enregistrée comme abandonnée"),
    ]
    screen = MenuScreen(app, "Quitter la partie ?", items, on_back=resume)
    screen.idle_logout = False
    return screen


class GameOverScreen(MenuScreen):
    """Fin de partie. Elle n'est enregistrée qu'en quittant cet écran, pour permettre
    de corriger la dernière fléchette."""

    idle_logout = False

    def __init__(self, app, game_screen: GameScreen):
        self.game_screen = game_screen
        game, players = game_screen.game, game_screen.players
        winner = players[game.winner].pseudo
        title = f"{winner} gagne !" if len(players) > 1 else "Partie terminée !"
        turns = [t for t in game.turns if t.player == game.winner]
        items = [
            Item("Rejouer", self.replay, "mêmes joueurs, mêmes règles"),
            Item("Menu principal", self.menu),
            Item("Corriger la dernière fléchette", self.correct),
        ]
        last = game.current_turn.darts[-1].label
        super().__init__(app, title, items, subtitle=f"Terminé en {len(turns)} volée(s), sur {last}")

    def _save(self) -> None:
        history.save_game(self.app.db, self.game_screen.game, self.game_screen.players)

    def replay(self) -> None:
        self._save()
        old = self.game_screen.game
        game = X01Game(old.player_count, old.start, old.double_out)
        self.app.show(GameScreen(self.app, self.game_screen.players, game))
        self.app.toast("Partie lancée !", theme.GREEN)

    def menu(self) -> None:
        from .menu import main_menu

        self._save()
        self.app.show(main_menu(self.app))

    def correct(self) -> None:
        self.game_screen.game.undo()
        self.app.show(self.game_screen)
