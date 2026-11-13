"""Écran de base et menu vertical générique, piloté par les trois boutons."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from .. import theme
from ..buttons import Action

if TYPE_CHECKING:
    from ..app import App


class Screen:
    # Déconnexion automatique après une période sans appui
    idle_logout = True

    def __init__(self, app: "App"):
        self.app = app

    def handle(self, action: Action) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass


@dataclass
class Item:
    label: str
    on_select: Callable[[], None] | None  # None : élément grisé, non sélectionnable
    detail: str = ""


class MenuScreen(Screen):
    """Liste d'éléments : Gauche / Droite pour se déplacer, appui court pour valider,
    appui long pour revenir en arrière (si on_back est défini)."""

    visible_rows = 7
    width = 1400
    hint = "Gauche / Droite : choisir  ·  appui court : valider  ·  appui long : retour"

    def __init__(self, app: "App", title: str, items: list[Item], subtitle: str = "",
                 on_back: Callable[[], None] | None = None):
        super().__init__(app)
        self.title = title
        self.subtitle = subtitle
        self.items = items
        self.on_back = on_back
        enabled = [i for i, item in enumerate(items) if item.on_select]
        self.index = enabled[0] if enabled else 0

    def _move(self, step: int) -> None:
        for _ in range(len(self.items)):
            self.index = (self.index + step) % len(self.items)
            if self.items[self.index].on_select:
                return

    def handle(self, action: Action) -> None:
        if action is Action.LEFT:
            self._move(-1)
        elif action is Action.RIGHT:
            self._move(1)
        elif action is Action.TRIPLE:
            if self.on_back:
                self.on_back()
        elif self.items and self.items[self.index].on_select:
            self.items[self.index].on_select()

    def draw(self, surface: pygame.Surface) -> None:
        theme.header(surface, self.title, self.subtitle)
        first = min(max(0, self.index - self.visible_rows // 2),
                    max(0, len(self.items) - self.visible_rows))
        y = 230
        for i in range(first, min(first + self.visible_rows, len(self.items))):
            item = self.items[i]
            rect = pygame.Rect(0, y, self.width, 96)
            rect.centerx = theme.WIDTH // 2
            theme.card(surface, rect, selected=(i == self.index))
            color = theme.WHITE if item.on_select else theme.MUTED
            theme.text(surface, item.label, 38, (rect.x + 40, rect.centery), color,
                       bold=True, anchor="midleft")
            if item.detail:
                theme.text(surface, item.detail, 26, (rect.right - 40, rect.centery),
                           theme.MUTED, anchor="midright")
            y += 110
        # Flèches : d'autres éléments au-dessus ou en dessous
        x = (theme.WIDTH + self.width) // 2 + 20
        if first > 0:
            pygame.draw.polygon(surface, theme.MUTED, [(x, 260), (x + 30, 260), (x + 15, 235)])
        if first + self.visible_rows < len(self.items):
            pygame.draw.polygon(surface, theme.MUTED, [(x, y - 60), (x + 30, y - 60), (x + 15, y - 35)])
        theme.footer(surface, self.hint if self.on_back else self.hint.rsplit("  ·  ", 1)[0])
