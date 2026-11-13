"""Affichage en direct des caméras sur l'écran, en mosaïque 2 x 2.

Test matériel : vérifie l'ouverture des caméras par leur port physique, le format
MJPEG et le débit d'images réel de chaque flux affiché par pygame.

Sur la Pi, depuis SSH :
    SDL_VIDEODRIVER=kmsdrm /opt/dartagnan/.venv/bin/python tools/camera_preview.py

Sans argument, toutes les caméras de /dev/v4l/by-path sont ouvertes. Une source
peut aussi être un fichier vidéo, pour tester sans caméra. Échap ou Q pour quitter.
"""

import argparse
import glob
import os
import threading
from pathlib import Path

import cv2
import numpy as np
import pygame


def find_cameras() -> list[str]:
    """Chemins by-path des flux image, un par caméra (les liens usbv2 sont des doublons)."""
    by_device = {
        os.path.realpath(p): p
        for p in sorted(glob.glob("/dev/v4l/by-path/*-usb-*-video-index0"))
    }
    return sorted(by_device.values())


class Camera:
    """Lit une source en continu dans un fil dédié et garde la dernière image."""

    def __init__(self, source: str, width: int, height: int, fps: int) -> None:
        self.name = Path(source).name
        api = cv2.CAP_V4L2 if source.startswith("/dev/") else cv2.CAP_ANY
        self.capture = cv2.VideoCapture(source, api)
        if not self.capture.isOpened():
            raise SystemExit(f"Ouverture impossible : {source}")
        # Le format doit être imposé avant la résolution pour que le pilote retienne MJPEG
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_FPS, fps)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        fourcc = (
            int(self.capture.get(cv2.CAP_PROP_FOURCC))
            .to_bytes(4, "little")
            .decode(errors="replace")
        )
        print(
            f"{self.name} : {fourcc} {int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))}"
            f"x{int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))} {self.capture.get(cv2.CAP_PROP_FPS):.0f} fps"
        )
        self.frame: np.ndarray | None = None
        self.count = 0
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _read_loop(self) -> None:
        while self.running:
            ok, frame = self.capture.read()
            if not ok:
                print(f"{self.name} : flux interrompu")
                return
            self.frame = frame
            self.count += 1

    def close(self) -> None:
        self.running = False
        self.thread.join(timeout=1)
        self.capture.release()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "sources",
        nargs="*",
        help="chemins des caméras ou fichiers vidéo (défaut : by-path)",
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    sources = args.sources or find_cameras()
    if not 1 <= len(sources) <= 4:
        raise SystemExit(
            f"Entre 1 et 4 sources attendues, {len(sources)} trouvées : {sources}"
        )
    cameras = [Camera(source, args.width, args.height, args.fps) for source in sources]

    pygame.display.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    tile_w, tile_h = screen.get_width() // 2, screen.get_height() // 2
    font = pygame.font.Font(None, 40)
    clock = pygame.time.Clock()
    rates = [0.0] * len(cameras)
    last_counts = [0] * len(cameras)
    last_tick = pygame.time.get_ticks()

    try:
        while not any(
            e.type == pygame.QUIT
            or (e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q))
            for e in pygame.event.get()
        ):
            now = pygame.time.get_ticks()
            if now - last_tick >= 1000:
                rates = [
                    (c.count - n) * 1000 / (now - last_tick)
                    for c, n in zip(cameras, last_counts)
                ]
                last_counts = [c.count for c in cameras]
                last_tick = now

            screen.fill((0, 0, 0))
            for i, camera in enumerate(cameras):
                x, y = (i % 2) * tile_w, (i // 2) * tile_h
                if camera.frame is not None:
                    tile = cv2.resize(
                        camera.frame, (tile_w, tile_h), interpolation=cv2.INTER_LINEAR
                    )
                    screen.blit(
                        pygame.image.frombuffer(
                            tile.tobytes(), (tile_w, tile_h), "BGR"
                        ),
                        (x, y),
                    )
                label = f"{i + 1}  {camera.name}  {rates[i]:.1f} img/s"
                screen.blit(
                    font.render(label, True, (255, 255, 0), (0, 0, 0)), (x + 8, y + 8)
                )
            pygame.display.flip()
            clock.tick(30)
    finally:
        for camera in cameras:
            camera.close()
        pygame.quit()


if __name__ == "__main__":
    main()
