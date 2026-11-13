"""Boucle principale : boutons, écran courant, messages temporaires."""

import os
import sqlite3
import time

import pygame

from ..storage.accounts import User
from . import theme
from .buttons import Button, Buttons
from .screens.account import login_screen
from .screens.base import Screen
from .screens.menu import main_menu

FPS = 30
IDLE_LOGOUT = 5 * 60   # secondes sans appui avant déconnexion (hors partie)
TOAST_SECONDS = 2.5

# Boutons simulés au clavier, en attendant le câblage des vrais boutons
KEYS = {
    pygame.K_LEFT: Button.LEFT,
    pygame.K_RIGHT: Button.RIGHT,
    pygame.K_RETURN: Button.SELECT,
    pygame.K_KP_ENTER: Button.SELECT,
    pygame.K_SPACE: Button.SELECT,
}


class App:
    def __init__(self, db: sqlite3.Connection, fullscreen: bool):
        self.db = db
        self.fullscreen = fullscreen
        self.user: User | None = None
        self.screen: Screen | None = None
        self.buttons = Buttons()
        self.last_input = time.monotonic()
        self._toast: tuple[str, tuple, float] | None = None

    def show(self, screen: Screen) -> None:
        self.screen = screen

    def toast(self, message: str, color=theme.TURQUOISE) -> None:
        self._toast = (message, color, time.monotonic() + TOAST_SECONDS)

    def log_in(self, user: User) -> None:
        self.user = user
        self.show(main_menu(self))

    def log_out(self) -> None:
        self.user = None
        self.show(login_screen(self))

    def run(self) -> None:
        pygame.display.init()
        pygame.font.init()
        if self.fullscreen:
            display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            pygame.mouse.set_visible(False)
        else:
            display = pygame.display.set_mode((theme.WIDTH // 2, theme.HEIGHT // 2), pygame.RESIZABLE)
        pygame.display.set_caption("Dartagnan")
        # Tout est dessiné en 1920 × 1080, puis mis à l'échelle si l'écran diffère
        canvas = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        clock = pygame.time.Clock()
        self.show(login_screen(self))

        while True:
            now = time.monotonic()
            actions = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.fullscreen:
                    return
                if event.type in (pygame.KEYDOWN, pygame.KEYUP) and event.key in KEYS:
                    if event.type == pygame.KEYDOWN:
                        actions += self.buttons.press(KEYS[event.key], now)
                    else:
                        actions += self.buttons.release(KEYS[event.key], now)
            actions += self.buttons.update(now)

            for action in actions:
                self.last_input = now
                self.screen.handle(action)
            if self.user and self.screen.idle_logout and now - self.last_input > IDLE_LOGOUT:
                self.log_out()
                self.toast("Déconnecté après 5 minutes d'inactivité")

            canvas.fill(theme.VIOLET)
            self.screen.draw(canvas)
            self._draw_toast(canvas, now)
            display = pygame.display.get_surface()
            if display.get_size() == canvas.get_size():
                display.blit(canvas, (0, 0))
            else:
                pygame.transform.smoothscale(canvas, display.get_size(), display)
            pygame.display.flip()
            clock.tick(FPS)

    def _draw_toast(self, surface: pygame.Surface, now: float) -> None:
        if not self._toast:
            return
        message, color, until = self._toast
        if now > until:
            self._toast = None
            return
        rendered = theme.font(36, bold=True).render(message, True, theme.VIOLET_DARK)
        rect = rendered.get_rect().inflate(80, 40)
        rect.midbottom = (theme.WIDTH // 2, theme.HEIGHT - 90)
        pygame.draw.rect(surface, color, rect, border_radius=rect.height // 2)
        surface.blit(rendered, rendered.get_rect(center=rect.center))


def is_fullscreen() -> bool:
    """Plein écran sur la Pi (affichage direct KMS/DRM), fenêtre sur un PC de développement."""
    return os.environ.get("SDL_VIDEODRIVER") == "kmsdrm"
