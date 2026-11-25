"""Enregistrement des volées réelles avec affichage en direct, pour mesurer et améliorer
la détection.

Plein écran, dessiné en 1920 × 1080 (mis à l'échelle si l'écran diffère) : les trois
caméras à gauche (grille de la cible calibrée, axe de la dernière fléchette), au centre
une cible de face avec la droite projetée par chaque caméra et les points d'impact, à
droite la volée en cours et le bilan de la séance.

Démarrer cible vide : Entrée calibre les caméras et ouvre la première volée. Quand
l'image bouge puis redevient stable, une photo de chaque caméra est prise et la
fléchette détectée s'affiche (3 par volée au plus). Ensuite : taper les zones réelles
dans l'ordre (20 T19 D5, 25, Bull, Out), retirer les fléchettes, Entrée : la volée est
enregistrée et la suivante commence sur la cible vide.

Touches : Entrée volée suivante, Suppr annule la dernière fléchette (fausse alerte),
Retour arrière corrige la saisie, Échap quitte.

Chaque volée va dans $DARTAGNAN_DATA/captures/<jjmmaa-hhmm>-voleeN/ : camN_<horodatage>.jpg
(cible vide, puis une photo par fléchette) et points.txt, au format de photos/ et de
tools/detect_photos.py.

    $env:PYTHONPATH="src"; $env:DARTAGNAN_DATA="data"
    .venv\\Scripts\\python tools\\record_volleys.py 1 2 3 --top 180 54 306
"""

import argparse
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pygame
from detect_photos import line_ends, same_zone

from dartagnan.capture.camera import Camera, find_cameras
from dartagnan.detection.dart import board_mask, dart_line
from dartagnan.detection.trigger import SMALL, ImpactTrigger, motion, small_gray
from dartagnan.display import theme
from dartagnan.game.darts import Dart
from dartagnan.geometry.auto_calibration import color_labels, detect
from dartagnan.geometry.board import (
    BULL_RADIUS,
    DOUBLE_INNER_RADIUS,
    DOUBLE_OUTER_RADIUS,
    OUTER_BULL_RADIUS,
    RING_RADII,
    SECTOR_ANGLE,
    SECTORS,
    TRIPLE_INNER_RADIUS,
    TRIPLE_OUTER_RADIUS,
    board_point,
    dart_at,
    sector_boundary,
)
from dartagnan.geometry.calibration import project
from dartagnan.geometry.triangulation import board_line, intersect

DARTS_PER_VOLLEY = 3
TILE_W, TILE_H = 640, 360  # vue de chaque caméra, empilées à gauche
BOARD_X, BOARD_Y, BOARD_SIZE = 660, 20, 820  # cible de face, au centre
HALF = 230.0  # mm affichés autour du centre de la cible
SCALE = BOARD_SIZE / (2 * HALF)  # px par mm
PANEL_X = 1510
CAMERA_COLORS = ((0, 220, 255), (255, 60, 200), (255, 230, 0))
RED, GREEN, BLACK, CREAM = (210, 35, 45), (25, 145, 70), (25, 25, 25), (235, 225, 195)
ZONE = re.compile(r"[TD]?(?:20|1[0-9]|[1-9])|25|BULL|50|OUT|RAT[EÉ]")


@dataclass
class Shot:
    """Une fléchette photographiée : photos, droites trouvées par caméra, position."""

    frames: list[np.ndarray]
    paths: list[Path]
    image_lines: list[np.ndarray | None]
    board_lines: list[np.ndarray | None]
    point: tuple[float, float] | None
    spread: float | None

    @property
    def dart(self) -> Dart | None:
        return None if self.point is None else dart_at(*self.point)


def parse_zones(text: str) -> list[str] | None:
    """Zones tapées (« 20 t19 bull ») au format de points.txt, None si l'une est invalide."""
    zones = text.upper().replace(",", " ").split()
    if not all(ZONE.fullmatch(z) for z in zones):
        return None
    names = {"BULL": "Bull", "50": "Bull", "OUT": "Out", "RATE": "Out", "RATÉ": "Out"}
    return [names.get(z, z) for z in zones]


def volley_folder(captures: Path) -> Path:
    """Dossier de la volée suivante, <jjmmaa-hhmm>-voleeN, N à la suite des volées du jour
    (le plus grand numéro + 1 : un dossier supprimé ne crée pas de doublon)."""
    now = time.localtime()
    day = time.strftime("%d%m%y", now)
    numbers = [
        int(n)
        for p in captures.glob(f"{day}-*-volee*")
        if (n := p.name.rsplit("volee", 1)[1]).isdigit()
    ]
    return (
        captures
        / f"{time.strftime('%d%m%y-%H%M', now)}-volee{max(numbers, default=0) + 1}"
    )


def save(folder: Path, frames: list[np.ndarray]) -> list[Path]:
    """Une photo par caméra, même horodatage à la milliseconde."""
    now = time.time()
    stamp = (
        time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
        + f"-{int(now * 1000) % 1000:03d}"
    )
    paths = [folder / f"cam{i + 1}_{stamp}.jpg" for i in range(len(frames))]
    for path, frame in zip(paths, frames):
        # cv2.imwrite échoue sans erreur, par exemple sur un chemin accentué
        if not cv2.imwrite(str(path), frame):
            raise SystemExit(f"Échec de l'enregistrement : {path}")
    return paths


def number(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def board_surface() -> pygame.Surface:
    """Cible de face aux couleurs d'une vraie cible, dessinée une fois."""
    size = 2 * BOARD_SIZE  # dessin en double taille puis réduction : bords lissés
    scale, center = 2 * SCALE, (BOARD_SIZE, BOARD_SIZE)
    surface = pygame.Surface((size, size), pygame.SRCALPHA)

    def at(angle: float, radius: float) -> tuple[float, float]:
        x, y = board_point(angle, radius)
        return BOARD_SIZE + x * scale, BOARD_SIZE - y * scale

    pygame.draw.circle(surface, BLACK, center, 225 * scale)
    bands = (  # (rayon intérieur, extérieur, anneau rouge et vert ?)
        (DOUBLE_INNER_RADIUS, DOUBLE_OUTER_RADIUS, True),
        (TRIPLE_OUTER_RADIUS, DOUBLE_INNER_RADIUS, False),
        (TRIPLE_INNER_RADIUS, TRIPLE_OUTER_RADIUS, True),
        (OUTER_BULL_RADIUS, TRIPLE_INNER_RADIUS, False),
    )
    for i in range(len(SECTORS)):
        start, end = sector_boundary(i - 1), sector_boundary(i)
        angles = [start + (end - start) * k / 8 for k in range(9)]
        for inner, outer, ring in bands:
            color = (RED, GREEN)[i % 2] if ring else (BLACK, CREAM)[i % 2]
            outline = [at(a, outer) for a in angles] + [
                at(a, inner) for a in reversed(angles)
            ]
            pygame.draw.polygon(surface, color, outline)
    pygame.draw.circle(surface, GREEN, center, OUTER_BULL_RADIUS * scale)
    pygame.draw.circle(surface, RED, center, BULL_RADIUS * scale)
    for i, sector in enumerate(SECTORS):
        theme.text(
            surface,
            str(sector),
            64,
            at(i * SECTOR_ANGLE, 197),
            bold=True,
            anchor="center",
        )
    return pygame.transform.smoothscale(surface, (BOARD_SIZE, BOARD_SIZE))


def to_board_view(line: np.ndarray) -> list[tuple[int, int]]:
    """Extrémités à l'écran d'une droite de la cible (mm), dans le carré de la cible."""
    a, b, c = line
    half = BOARD_SIZE / 2
    local = np.array([a, -b, c * SCALE + (b - a) * half])
    return [
        (x + BOARD_X, y + BOARD_Y) for x, y in line_ends(local, BOARD_SIZE, BOARD_SIZE)
    ]


def label(
    canvas: pygame.Surface,
    value: str,
    pos: tuple[int, int],
    color=theme.WHITE,
    size: int = 22,
) -> None:
    """Texte sur fond sombre, lisible sur une image de caméra ou sur la cible."""
    rendered = theme.font(size, True).render(value, True, color)
    rect = rendered.get_rect(topleft=pos).inflate(12, 4)
    pygame.draw.rect(canvas, (0, 0, 0), rect, border_radius=6)
    canvas.blit(rendered, pos)


class Recorder:
    """État de la séance : calibration, volée en cours, saisie, bilan."""

    def __init__(
        self, cameras: list[Camera], tops: list[float], captures: Path
    ) -> None:
        self.cameras, self.tops, self.captures = cameras, tops, captures
        self.board = board_surface()
        self.homographies: list[np.ndarray] | None = None
        self.shots: list[Shot] = []
        self.typed = ""
        self.calibrating = False
        self.running = True
        self.trigger = ImpactTrigger()
        self.amount = 0.0
        self.notice, self.notice_until = "", 0.0
        self.right = self.total = 0
        self.rates = [0.0] * len(cameras)
        self.counts, self.counted_at = [c.count for c in cameras], time.monotonic()

    def say(self, message: str) -> None:
        self.notice, self.notice_until = message, time.monotonic() + 6

    # Calibration et volées

    def calibrate(self) -> None:
        self.calibrating = False
        frames = [c.frame for c in self.cameras]
        if any(f is None for f in frames):
            self.say("Une caméra ne donne pas d'image : vérifier le branchement.")
            return
        homographies, self.errors = [], []
        for i, (frame, top) in enumerate(zip(frames, self.tops)):
            result = detect(color_labels(frame), top=top)
            pygame.event.pump()  # fenêtre réactive pendant les quelques secondes de calcul
            if result is None:
                self.say(f"Caméra {i + 1} : cible non trouvée. Vérifier puis Entrée.")
                return
            homographies.append(result[0])
            self.errors.append(result[1])
        self.homographies = homographies
        self.masks = [board_mask(h, f.shape) for h, f in zip(homographies, frames)]
        self.small_masks = [cv2.resize(m, None, fx=SMALL, fy=SMALL) for m in self.masks]
        self.grids = [
            self.grid(i, h, f.shape[1])
            for i, (h, f) in enumerate(zip(homographies, frames))
        ]
        self.open_volley(frames)

    def grid(self, i: int, homography: np.ndarray, width: int) -> list[np.ndarray]:
        """Anneaux et limites des secteurs projetés dans la vue de la caméra i."""
        shapes = [[board_point(a, r) for a in range(0, 361, 4)] for r in RING_RADII]
        shapes += [
            [
                board_point(sector_boundary(k), r)
                for r in (OUTER_BULL_RADIUS, DOUBLE_OUTER_RADIUS)
            ]
            for k in range(len(SECTORS))
        ]
        return [
            project(homography, s) * (TILE_W / width) + (0, i * TILE_H) for s in shapes
        ]

    def open_volley(self, frames: list[np.ndarray]) -> None:
        self.folder = volley_folder(self.captures)
        self.folder.mkdir(parents=True)
        save(self.folder, frames)
        self.empty = frames
        self.shots = []
        self.typed = ""
        self.previous = [small_gray(f) for f in frames]
        self.trigger.reset()
        print(f"Nouvelle volée : {self.folder}")

    def capture(self, frames: list[np.ndarray]) -> None:
        """La fléchette vient de se planter : photos, axes, droites, position."""
        before = self.shots[-1].frames if self.shots else self.empty
        image_lines = [
            dart_line(b, a, m) for b, a, m in zip(before, frames, self.masks)
        ]
        board_lines = [
            None if line is None else board_line(h, line)
            for h, line in zip(self.homographies, image_lines)
        ]
        found = intersect([line for line in board_lines if line is not None])
        point, spread = found if found else (None, None)
        shot = Shot(
            frames, save(self.folder, frames), image_lines, board_lines, point, spread
        )
        self.shots.append(shot)
        print(
            f"Fléchette {len(self.shots)} : {shot.dart.label if shot.dart else 'non détectée'}"
        )

    def undo(self) -> None:
        """Fausse alerte : photos et fléchette supprimées, la suivante est comparée à la
        photo d'avant."""
        if self.shots:
            for path in self.shots.pop().paths:
                path.unlink()

    def save_zones(self) -> bool:
        """Écrit points.txt si les zones tapées sont valides, une par fléchette."""
        zones = parse_zones(self.typed)
        if zones is None:
            self.say("Zone invalide : 1 à 20, T ou D devant, 25, Bull ou Out.")
            return False
        if zones and len(zones) != len(self.shots):
            self.say(
                f"{len(self.shots)} zones attendues, une par fléchette photographiée."
            )
            return False
        if not zones:
            print(f"Volée sans zones réelles : {self.folder}")
            return True
        (self.folder / "points.txt").write_text(
            "\n".join(zones) + "\n", encoding="utf-8"
        )
        self.right += sum(same_zone(z, s.dart) for z, s in zip(zones, self.shots))
        self.total += len(zones)
        return True

    def next_volley(self) -> None:
        if not self.shots:
            self.say("Aucune fléchette photographiée dans cette volée.")
        elif self.save_zones():
            self.open_volley([c.frame for c in self.cameras])

    def close(self) -> None:
        """Volée vide supprimée, zones de la dernière volée enregistrées si valides."""
        if self.homographies is None:
            return
        if not self.shots:
            for path in self.folder.iterdir():
                path.unlink()
            self.folder.rmdir()
        elif not self.save_zones():
            print(f"Zones non enregistrées ({self.notice}) : {self.folder}")

    # Boucle

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.homographies is None:
                    self.calibrating = True
                else:
                    self.next_volley()
            elif event.key == pygame.K_DELETE:
                self.undo()
            elif event.key == pygame.K_BACKSPACE:
                self.typed = self.typed[:-1]
        elif event.type == pygame.TEXTINPUT:
            allowed = "".join(c for c in event.text if c.isalnum() or c in " ,")
            self.typed = (self.typed + allowed)[:40]

    def update(self) -> None:
        now = time.monotonic()
        if now - self.counted_at >= 1:
            counts = [c.count for c in self.cameras]
            self.rates = [
                (n - m) / (now - self.counted_at) for n, m in zip(counts, self.counts)
            ]
            self.counts, self.counted_at = counts, now
        if self.calibrating:
            self.calibrate()
        if self.homographies is None:
            return
        frames = [c.frame for c in self.cameras]  # images remplacées, jamais modifiées
        small = [small_gray(f) for f in frames]
        self.amount = max(
            motion(p, n, m) for p, n, m in zip(self.previous, small, self.small_masks)
        )
        self.previous = small
        if self.trigger.update(self.amount) and len(self.shots) < DARTS_PER_VOLLEY:
            self.capture(frames)

    # Affichage

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(theme.VIOLET_DARK)
        for i in range(len(self.cameras)):
            self.draw_camera(canvas, i)
        canvas.blit(self.board, (BOARD_X, BOARD_Y))
        self.draw_impacts(canvas)
        self.draw_panel(canvas)
        self.draw_status(canvas)

    def draw_camera(self, canvas: pygame.Surface, i: int) -> None:
        y = i * TILE_H
        frame = self.cameras[i].frame
        if frame is None:
            theme.text(
                canvas,
                "Pas d'image",
                30,
                (TILE_W // 2, y + TILE_H // 2),
                theme.PINK,
                anchor="center",
            )
        else:
            tile = cv2.resize(frame, (TILE_W, TILE_H))
            canvas.blit(
                pygame.image.frombuffer(tile.tobytes(), (TILE_W, TILE_H), "BGR"), (0, y)
            )
        canvas.set_clip(pygame.Rect(0, y, TILE_W, TILE_H))
        if self.homographies is not None:
            for shape in self.grids[i]:
                pygame.draw.lines(canvas, (0, 255, 0), False, shape.tolist(), 1)
        color = CAMERA_COLORS[i % len(CAMERA_COLORS)]
        if self.shots:
            line = self.shots[-1].image_lines[i]
            if line is None:
                label(
                    canvas,
                    "Pas d'axe pour la dernière fléchette",
                    (10, y + TILE_H - 34),
                    theme.PINK,
                )
            else:
                scale = TILE_W / frame.shape[1]
                ends = line_ends(
                    np.array([line[0], line[1], line[2] * scale]), TILE_W, TILE_H
                )
                if len(ends) == 2:
                    pygame.draw.line(
                        canvas,
                        color,
                        (ends[0][0], ends[0][1] + y),
                        (ends[1][0], ends[1][1] + y),
                        3,
                    )
        canvas.set_clip(None)
        name = f"Caméra {i + 1}   {number(self.rates[i], 0)} img/s"
        if self.homographies is not None:
            name += f"   calibration {number(self.errors[i])} mm"
        label(canvas, name, (10, y + 8), color)

    def draw_impacts(self, canvas: pygame.Surface) -> None:
        canvas.set_clip(pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE))
        if self.shots:
            for i, line in enumerate(self.shots[-1].board_lines):
                ends = [] if line is None else to_board_view(line)
                if len(ends) == 2:
                    pygame.draw.line(
                        canvas,
                        CAMERA_COLORS[i % len(CAMERA_COLORS)],
                        ends[0],
                        ends[1],
                        2,
                    )
        zones = parse_zones(self.typed) or []
        for k, shot in enumerate(self.shots):
            if shot.point is None:
                continue
            x = round(BOARD_X + BOARD_SIZE / 2 + shot.point[0] * SCALE)
            y = round(BOARD_Y + BOARD_SIZE / 2 - shot.point[1] * SCALE)
            fill = theme.WHITE
            if k < len(zones):
                fill = theme.GREEN if same_zone(zones[k], shot.dart) else RED
            pygame.draw.circle(canvas, (0, 0, 0), (x, y), 15)
            pygame.draw.circle(canvas, fill, (x, y), 12)
            theme.text(
                canvas, str(k + 1), 18, (x, y), (0, 0, 0), bold=True, anchor="center"
            )
            label(canvas, shot.dart.label, (x + 20, y - 12))
        canvas.set_clip(None)

    def draw_panel(self, canvas: pygame.Surface) -> None:
        x = PANEL_X
        if self.homographies is None:
            theme.text(canvas, "Calibration", 44, (x, 30), bold=True)
            theme.text(canvas, "Caméras et cible fixes,", 24, (x, 100), theme.MUTED)
            theme.text(canvas, "cible vide.", 24, (x, 132), theme.MUTED)
            return
        theme.text(
            canvas,
            f"Volée {self.folder.name.rsplit('volee', 1)[1]}",
            48,
            (x, 24),
            bold=True,
        )
        theme.text(canvas, self.folder.name, 22, (x, 86), theme.MUTED)
        zones = parse_zones(self.typed) or []
        y = 140
        for k in range(DARTS_PER_VOLLEY):
            theme.text(canvas, f"Fléchette {k + 1}", 28, (x, y), bold=True)
            if k < len(self.shots):
                shot = self.shots[k]
                seen = sum(line is not None for line in shot.board_lines)
                found = f"Détectée : {shot.dart.label}" if shot.dart else "Non détectée"
                theme.text(canvas, found, 26, (x, y + 38))
                detail = f"{seen} caméra{'s' if seen > 1 else ''}"
                if shot.spread is not None:
                    detail += f", écart {number(shot.spread)} mm"
                theme.text(canvas, detail, 22, (x, y + 72), theme.MUTED)
                if k < len(zones):
                    ok = same_zone(zones[k], shot.dart)
                    theme.text(
                        canvas,
                        f"Réelle : {zones[k]}",
                        26,
                        (x, y + 102),
                        theme.GREEN if ok else theme.ORANGE,
                        bold=True,
                    )
            else:
                theme.text(canvas, "en attente", 24, (x, y + 38), theme.MUTED)
            y += 150
        theme.text(canvas, "Zones réelles", 26, (x, y + 10), bold=True)
        box = pygame.Rect(x, y + 48, 390, 56)
        valid = parse_zones(self.typed) is not None
        theme.card(
            canvas,
            box,
            fill=theme.VIOLET,
            border=theme.TURQUOISE if valid else theme.ORANGE,
        )
        cursor = "|" if int(time.monotonic() * 2) % 2 else ""
        theme.text(canvas, self.typed + cursor, 28, (x + 14, y + 60))
        y += 130
        if self.total:
            share = round(100 * self.right / self.total)
            theme.text(
                canvas,
                f"Séance : {self.right} / {self.total} justes ({share} %)",
                26,
                (x, y),
                theme.TURQUOISE,
                bold=True,
            )
        theme.text(
            canvas,
            f"Mouvement {number(100 * self.amount, 2)} %",
            22,
            (x, y + 40),
            theme.ORANGE if self.trigger.moved else theme.MUTED,
        )

    def draw_status(self, canvas: pygame.Surface) -> None:
        x, y = BOARD_X, BOARD_Y + BOARD_SIZE + 20
        if self.calibrating:
            status = "Calibration en cours…"
        elif self.homographies is None:
            status = "Cible vide, personne devant : Entrée pour calibrer et commencer."
        elif len(self.shots) >= DARTS_PER_VOLLEY:
            status = "Volée complète : taper les zones, retirer les fléchettes, Entrée."
        elif self.trigger.moved:
            status = "Mouvement…"
        else:
            status = f"En attente de la fléchette {len(self.shots) + 1}."
        theme.text(canvas, status, 30, (x, y), theme.TURQUOISE, bold=True)
        if self.notice and time.monotonic() < self.notice_until:
            theme.text(canvas, self.notice, 26, (x, y + 50), theme.PINK, bold=True)
        theme.text(
            canvas,
            "Entrée : volée suivante    Suppr : annuler la dernière fléchette    "
            "Retour arrière : corriger    Échap : quitter",
            20,
            (x, theme.HEIGHT - 36),
            theme.MUTED,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("sources", nargs="*", help="numéros de caméra (PC) ou by-path")
    parser.add_argument("--top", type=float, nargs="+", default=[180.0, 54.0, 306.0])
    args = parser.parse_args()

    sources = args.sources or find_cameras()
    if len(args.top) != len(sources):
        raise SystemExit(f"--top : {len(sources)} valeurs attendues, une par source")
    data = Path(os.environ.get("DARTAGNAN_DATA", "/var/lib/dartagnan"))
    cameras = [Camera(s, 1280, 720, 30) for s in sources]
    # Plein écran en pixels réels : sans ce réglage, Windows agrandit lui-même une
    # fenêtre sur un écran mis à l'échelle (125 %, 150 %) et l'image devient floue
    os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Dartagnan : volées en direct")
    canvas = pygame.Surface((theme.WIDTH, theme.HEIGHT))
    clock = pygame.time.Clock()
    recorder = Recorder(cameras, args.top, data / "captures")
    try:
        while recorder.running:
            for event in pygame.event.get():
                recorder.handle(event)
            recorder.draw(canvas)
            window = pygame.display.get_surface()
            pygame.transform.smoothscale(canvas, window.get_size(), window)
            pygame.display.flip()
            recorder.update()  # après l'affichage : « Calibration en cours » visible avant
            clock.tick(30)
    finally:
        recorder.close()
        for camera in cameras:
            camera.close()
        pygame.quit()


if __name__ == "__main__":
    main()
