"""Affichage en direct des caméras sur l'écran, en mosaïque 2 x 2.

Test matériel : vérifie l'ouverture des caméras par leur port physique, le format
MJPEG et le débit d'images réel de chaque flux affiché par pygame.

Sur la Pi, depuis /opt/dartagnan :
    PYTHONPATH=src SDL_VIDEODRIVER=kmsdrm .venv/bin/python tools/camera_preview.py

Sur PC Windows, caméras par numéro :
    PYTHONPATH=src .venv/Scripts/python tools/camera_preview.py 0 1 2

Sans argument, toutes les caméras de /dev/v4l/by-path sont ouvertes (Pi). Une source
peut aussi être un fichier vidéo, pour tester sans caméra. Échap ou Q pour quitter.
"""

import argparse

import cv2
import pygame

from dartagnan.capture.camera import Camera, find_cameras


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
