"""Charte graphique JUNIA (septembre 2025) et outils de dessin communs.

Violet dominant (obligatoire en fond quand le logo est affiché), orange
institutionnel pour la sélection, couleurs secondaires par touches.
Police Montserrat ; police par défaut de pygame si elle n'est pas installée.
"""

from functools import cache
from pathlib import Path

import pygame

WIDTH, HEIGHT = 1920, 1080

# Couleurs institutionnelles
VIOLET = (63, 42, 86)        # #3F2A56
ORANGE = (255, 92, 57)       # #FF5C39
# Couleurs secondaires
TURQUOISE = (97, 202, 208)   # #61CAD0
GREEN = (47, 173, 102)       # #2FAD66
TEAL = (0, 104, 128)         # #006880
PINK = (255, 185, 181)       # #FFB9B5
# Nuances du violet pour les cartes et les textes
VIOLET_DARK = (46, 30, 64)
VIOLET_LIGHT = (84, 60, 112)
WHITE = (255, 255, 255)
MUTED = (190, 178, 206)

ASSETS = Path(__file__).parent / "assets"


@cache
def font(size: int, bold: bool = False) -> pygame.font.Font:
    path = pygame.font.match_font("montserrat", bold=bold)
    return pygame.font.Font(path, size)  # path None : police par défaut de pygame


@cache
def logo(height: int) -> pygame.Surface:
    """Bloc-marque JUNIA blanc, à afficher uniquement sur fond violet."""
    image = pygame.image.load(ASSETS / "logo_junia_blanc.png").convert_alpha()
    image = image.subsurface(image.get_bounding_rect())
    width = round(image.get_width() * height / image.get_height())
    return pygame.transform.smoothscale(image, (width, height))


def text(surface: pygame.Surface, value: str, size: int, pos: tuple[int, int],
         color=WHITE, bold: bool = False, anchor: str = "topleft") -> pygame.Rect:
    """Écrit un texte ; anchor est un attribut de pygame.Rect (center, midtop…)."""
    rendered = font(size, bold).render(value, True, color)
    rect = rendered.get_rect(**{anchor: pos})
    surface.blit(rendered, rect)
    return rect


def card(surface: pygame.Surface, rect: pygame.Rect, selected: bool = False,
         fill=VIOLET_DARK, border=None) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=18)
    if selected:
        pygame.draw.rect(surface, ORANGE, rect, width=6, border_radius=18)
    elif border:
        pygame.draw.rect(surface, border, rect, width=3, border_radius=18)


def header(surface: pygame.Surface, title: str, subtitle: str = "") -> None:
    """Bandeau du haut : logo JUNIA, nom du jeu et titre de l'écran."""
    surface.blit(logo(70), (48, 30))
    text(surface, "DARTAGNAN", 34, (WIDTH // 2, 36), ORANGE, bold=True, anchor="midtop")
    text(surface, title, 52, (WIDTH // 2, 80), bold=True, anchor="midtop")
    if subtitle:
        text(surface, subtitle, 28, (WIDTH // 2, 148), MUTED, anchor="midtop")


def footer(surface: pygame.Surface, hint: str) -> None:
    text(surface, hint, 26, (WIDTH // 2, HEIGHT - 30), MUTED, anchor="midbottom")
