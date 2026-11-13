"""Trois boutons physiques : Gauche, Droite, Valider.

Transforme les appuis et relâchements en actions de l'interface :
- Gauche / Droite : LEFT / RIGHT, répétés tant que le bouton reste enfoncé ;
- Valider : SINGLE (appui court), DOUBLE (deux appuis rapides), TRIPLE (appui long).

Indépendant de la source des appuis : clavier aujourd'hui, GPIO plus tard.
Les temps sont en secondes et passés en paramètre, pour pouvoir tester sans attendre.
"""

from enum import Enum


class Button(Enum):
    LEFT = "gauche"
    RIGHT = "droite"
    SELECT = "valider"


class Action(Enum):
    LEFT = "gauche"
    RIGHT = "droite"
    SINGLE = "simple"
    DOUBLE = "double"
    TRIPLE = "triple"


LONG_PRESS = 0.6       # appui maintenu au-delà : triple
DOUBLE_WINDOW = 0.3    # délai max entre deux appuis pour un double
REPEAT_DELAY = 0.4     # Gauche / Droite maintenu : début de la répétition
REPEAT_INTERVAL = 0.1


class Buttons:
    def __init__(self):
        self._select_pressed_at: float | None = None   # Valider enfoncé depuis
        self._select_released_at: float | None = None  # 1er appui court relâché, en attente d'un 2e
        self._select_consumed = False                  # action déjà émise pour cet appui
        self._repeat: dict[Button, float] = {}         # prochaine répétition de Gauche / Droite

    def press(self, button: Button, now: float) -> list[Action]:
        if button is Button.SELECT:
            if self._select_released_at is not None:
                self._select_released_at = None
                self._select_consumed = True
                return [Action.DOUBLE]
            self._select_pressed_at = now
            self._select_consumed = False
            return []
        self._repeat[button] = now + REPEAT_DELAY
        return [Action(button.value)]

    def release(self, button: Button, now: float) -> list[Action]:
        if button is Button.SELECT:
            if self._select_pressed_at is not None and not self._select_consumed:
                self._select_released_at = now
            self._select_pressed_at = None
            self._select_consumed = False
        else:
            self._repeat.pop(button, None)
        return []

    def update(self, now: float) -> list[Action]:
        """À appeler à chaque image : émet les actions qui dépendent du temps écoulé."""
        actions = []
        if (self._select_pressed_at is not None and not self._select_consumed
                and now - self._select_pressed_at >= LONG_PRESS):
            self._select_consumed = True
            actions.append(Action.TRIPLE)
        if self._select_released_at is not None and now - self._select_released_at > DOUBLE_WINDOW:
            self._select_released_at = None
            actions.append(Action.SINGLE)
        for button, at in self._repeat.items():
            if now >= at:
                self._repeat[button] = now + REPEAT_INTERVAL
                actions.append(Action(button.value))
        return actions
