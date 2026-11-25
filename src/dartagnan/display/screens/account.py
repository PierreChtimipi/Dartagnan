"""Connexion et création de compte : pseudo composé aux boutons, code PIN."""

from collections.abc import Callable
from string import ascii_uppercase, digits

import pygame

from ...storage import accounts
from .. import theme
from ..buttons import Action
from .base import Item, MenuScreen, Screen

BACKSPACE = "Effacer"
OK = "OK"


class KeypadScreen(Screen):
    """Grille de touches parcourue avec Gauche / Droite. Appui court : taper la touche.
    Appui long : retour. Le texte saisi est masqué pour un code PIN."""

    columns = 10

    def __init__(self, app, title: str, keys: list[str], max_length: int,
                 on_submit: Callable[[str], str | None], on_back: Callable[[], None],
                 secret: bool = False, subtitle: str = ""):
        super().__init__(app)
        self.title = title
        self.subtitle = subtitle
        self.keys = keys + [BACKSPACE, OK]
        self.max_length = max_length
        self.on_submit = on_submit  # renvoie un message d'erreur, ou None si accepté
        self.on_back = on_back
        self.secret = secret
        self.value = ""
        self.index = 0
        self.error = ""

    def handle(self, action: Action) -> None:
        if action is Action.LEFT:
            self.index = (self.index - 1) % len(self.keys)
        elif action is Action.RIGHT:
            self.index = (self.index + 1) % len(self.keys)
        elif action is Action.TRIPLE:
            self.on_back()
        else:
            key = self.keys[self.index]
            self.error = ""
            if key == OK:
                error = self.on_submit(self.value)
                if error:
                    self.error = error
                    if self.secret:
                        self.value = ""
                return
            # Deux appuis rapides tapent la touche deux fois
            for _ in range(2 if action is Action.DOUBLE else 1):
                if key == BACKSPACE:
                    self.value = self.value[:-1]
                elif len(self.value) < self.max_length:
                    self.value += key

    def draw(self, surface: pygame.Surface) -> None:
        theme.header(surface, self.title, self.subtitle)
        shown = "*" * len(self.value) if self.secret else self.value
        box = pygame.Rect(0, 220, 900, 120)
        box.centerx = theme.WIDTH // 2
        theme.card(surface, box, border=theme.VIOLET_LIGHT)
        theme.text(surface, shown or "_", 64, box.center, bold=True, anchor="center")
        if self.error:
            theme.text(surface, self.error, 32, (theme.WIDTH // 2, 370), theme.PINK,
                       bold=True, anchor="midtop")

        size, gap = 150, 16
        rows = -(-len(self.keys) // self.columns)
        left = (theme.WIDTH - self.columns * size - (self.columns - 1) * gap) // 2
        top = 440 if rows <= 2 else 430
        for i, key in enumerate(self.keys):
            row, col = divmod(i, self.columns)
            rect = pygame.Rect(left + col * (size + gap), top + row * (110 + gap), size, 110)
            fill = theme.TEAL if key == OK else theme.VIOLET_DARK
            theme.card(surface, rect, selected=(i == self.index), fill=fill)
            theme.text(surface, key, 44 if len(key) < 3 else 28, rect.center, bold=True, anchor="center")
        theme.footer(surface, "Gauche / Droite : choisir  ·  appui court : taper  ·  appui long : retour")


def login_screen(app) -> MenuScreen:
    users = accounts.list_users(app.db)
    items = [Item(u.pseudo, lambda u=u: app.show(pin_login_screen(app, u))) for u in users]
    items.append(Item("+ Créer un compte", lambda: app.show(pseudo_screen(app))))
    return MenuScreen(app, "Qui joue ?", items, subtitle="Choisis ton compte")


def pin_login_screen(app, user: accounts.User) -> KeypadScreen:
    def submit(pin: str) -> str | None:
        try:
            app.log_in(accounts.login(app.db, user.id, pin))
        except accounts.AccountError as error:
            return str(error)
        return None

    return KeypadScreen(app, user.pseudo, list("1234567890"), 6, submit,
                        on_back=lambda: app.show(login_screen(app)), secret=True,
                        subtitle="Entre ton code")


def pseudo_screen(app) -> KeypadScreen:
    def submit(pseudo: str) -> str | None:
        try:
            accounts.validate_pseudo(pseudo)
        except accounts.AccountError as error:
            return str(error)
        if accounts.pseudo_exists(app.db, pseudo):
            return "Ce pseudo est déjà pris"
        app.show(new_pin_screen(app, pseudo))
        return None

    keys = list(ascii_uppercase) + list(digits) + ["-", "_"]
    return KeypadScreen(app, "Nouveau compte", keys, 16, submit,
                        on_back=lambda: app.show(login_screen(app)),
                        subtitle="Choisis ton pseudo (3 à 16 caractères)")


def new_pin_screen(app, pseudo: str) -> KeypadScreen:
    def submit(pin: str) -> str | None:
        try:
            accounts.validate_pin(pin)
        except accounts.AccountError as error:
            return str(error)
        app.show(confirm_pin_screen(app, pseudo, pin))
        return None

    return KeypadScreen(app, pseudo, list("1234567890"), 6, submit,
                        on_back=lambda: app.show(login_screen(app)), secret=True,
                        subtitle="Choisis un code de 4 à 6 chiffres")


def confirm_pin_screen(app, pseudo: str, first_pin: str) -> KeypadScreen:
    def submit(pin: str) -> str | None:
        if pin != first_pin:
            app.show(new_pin_screen(app, pseudo))
            app.toast("Les codes ne correspondent pas", theme.PINK)
            return None
        try:
            app.log_in(accounts.create_account(app.db, pseudo, pin))
        except accounts.AccountError as error:
            return str(error)
        app.toast(f"Bienvenue {pseudo} !", theme.GREEN)
        return None

    return KeypadScreen(app, pseudo, list("1234567890"), 6, submit,
                        on_back=lambda: app.show(login_screen(app)), secret=True,
                        subtitle="Confirme ton code")
