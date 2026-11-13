"""Une fléchette : secteur touché et multiplicateur."""

from dataclasses import dataclass

BULL = 25  # secteur du centre : 25 en simple, 50 (Bull) en double
MISS = 0   # fléchette hors cible


@dataclass(frozen=True)
class Dart:
    segment: int     # 1 à 20, BULL (25) ou MISS (0)
    multiplier: int  # 1 simple, 2 double, 3 triple

    def __post_init__(self):
        if self.multiplier not in (1, 2, 3):
            raise ValueError(f"Multiplicateur invalide : {self.multiplier}")
        if self.segment == MISS:
            if self.multiplier != 1:
                raise ValueError("Une fléchette ratée n'a pas de multiplicateur")
        elif self.segment == BULL:
            if self.multiplier == 3:
                raise ValueError("Le triple Bull n'existe pas")
        elif not 1 <= self.segment <= 20:
            raise ValueError(f"Secteur invalide : {self.segment}")

    @property
    def points(self) -> int:
        return self.segment * self.multiplier

    @property
    def is_double(self) -> bool:
        return self.multiplier == 2

    @property
    def label(self) -> str:
        if self.segment == MISS:
            return "Raté"
        if self.segment == BULL:
            return "Bull" if self.multiplier == 2 else "25"
        return ("", "D", "T")[self.multiplier - 1] + str(self.segment)
