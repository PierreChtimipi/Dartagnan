"""Règles du 301 (et plus généralement des jeux X01).

L'état de la partie est recalculé à partir de la liste des fléchettes lancées :
annuler une fléchette revient simplement à la retirer de la liste.
"""

from dataclasses import dataclass, field

from .darts import Dart

DARTS_PER_TURN = 3


@dataclass
class Turn:
    """Une volée : jusqu'à 3 fléchettes d'un joueur."""
    player: int        # index du joueur dans la partie
    number: int        # numéro de la volée pour ce joueur, à partir de 1
    score_before: int  # score restant au début de la volée
    darts: list[Dart] = field(default_factory=list)
    bust: bool = False

    @property
    def points(self) -> int:
        """Points réellement retirés : 0 en cas de bust."""
        return 0 if self.bust else sum(d.points for d in self.darts)

    @property
    def score_after(self) -> int:
        return self.score_before - self.points


class X01Game:
    def __init__(self, player_count: int, start: int = 301, double_out: bool = False):
        if player_count < 1:
            raise ValueError("Il faut au moins un joueur")
        self.player_count = player_count
        self.start = start
        self.double_out = double_out
        self._darts: list[Dart] = []
        self._replay()

    def throw(self, dart: Dart) -> None:
        if self.winner is not None:
            raise RuntimeError("La partie est terminée")
        self._darts.append(dart)
        self._replay()

    def undo(self) -> Dart | None:
        """Retire la dernière fléchette, même si elle a terminé une volée ou la partie."""
        if not self._darts:
            return None
        dart = self._darts.pop()
        self._replay()
        return dart

    @property
    def is_over(self) -> bool:
        return self.winner is not None

    @property
    def current_turn(self) -> Turn:
        """Volée en cours (pour une partie finie : la dernière volée)."""
        return self.turns[-1]

    @property
    def current_player(self) -> int:
        return self.current_turn.player

    def _is_bust(self, remaining: int, dart: Dart) -> bool:
        if remaining < 0:
            return True
        if self.double_out:
            # Il faut finir sur un double : rester à 1 est impossible à terminer
            return remaining == 1 or (remaining == 0 and not dart.is_double)
        return False

    def _replay(self) -> None:
        # scores : score de chaque joueur au début de sa volée en cours
        self.scores = [self.start] * self.player_count
        self.turns: list[Turn] = []
        self.winner: int | None = None
        self._new_turn(0)
        for dart in self._darts:
            turn = self.turns[-1]
            turn.darts.append(dart)
            remaining = turn.score_before - sum(d.points for d in turn.darts)
            if self._is_bust(remaining, dart):
                turn.bust = True
            elif remaining == 0:
                self.scores[turn.player] = 0
                self.winner = turn.player
                break
            if turn.bust or len(turn.darts) == DARTS_PER_TURN:
                self.scores[turn.player] = turn.score_after
                self._new_turn((turn.player + 1) % self.player_count)

    def _new_turn(self, player: int) -> None:
        number = sum(1 for t in self.turns if t.player == player) + 1
        self.turns.append(Turn(player, number, self.scores[player]))

    def turn_in_progress_score(self) -> int:
        """Score restant affiché pour le joueur en cours, fléchettes de la volée comprises."""
        turn = self.current_turn
        if turn.bust:
            return turn.score_before
        return turn.score_before - sum(d.points for d in turn.darts)

    @property
    def played_turns(self) -> list[Turn]:
        """Volées contenant au moins une fléchette, à enregistrer dans l'historique."""
        return [t for t in self.turns if t.darts]
