"""Acquisition d'une caméra, ou d'une source simulée (fichier vidéo ou image).

Sources acceptées :
- chemin `/dev/v4l/by-path/...` : caméra sur la Pi (V4L2) ;
- numéro (`0`, `1`, `2`) : caméra sur un PC Windows (DirectShow), développement uniquement ;
- tout autre chemin : fichier vidéo ou image, lu comme une caméra.
"""

import glob
import os
import threading
from pathlib import Path

import cv2
import numpy as np


def find_cameras() -> list[str]:
    """Chemins by-path des flux image, un par caméra (les liens usbv2 sont des doublons)."""
    by_device = {
        os.path.realpath(p): p
        for p in sorted(glob.glob("/dev/v4l/by-path/*-usb-*-video-index0"))
    }
    return sorted(by_device.values())


def _open(source: str) -> cv2.VideoCapture:
    if source.isdigit():
        # Les numéros Windows changent selon l'ordre de branchement : jamais sur la Pi
        return cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
    if source.startswith("/dev/"):
        return cv2.VideoCapture(source, cv2.CAP_V4L2)
    return cv2.VideoCapture(source)


class Camera:
    """Lit une source en continu dans un fil dédié et garde la dernière image."""

    def __init__(self, source: str, width: int, height: int, fps: int) -> None:
        self.source = source
        self.name = Path(source).name
        self.capture = _open(source)
        if not self.capture.isOpened():
            raise SystemExit(f"Ouverture impossible : {source}")
        mjpg = cv2.VideoWriter.fourcc(*"MJPG")
        if source.isdigit():
            # DirectShow (PC) : MJPEG retenu seulement s'il est imposé après la résolution,
            # images/s laissées au pilote (mesuré sur PC : environ 28 img/s par caméra)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.capture.set(cv2.CAP_PROP_FOURCC, mjpg)
        else:
            # V4L2 (Pi) : le format doit être imposé avant la résolution pour être retenu
            self.capture.set(cv2.CAP_PROP_FOURCC, mjpg)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.capture.set(cv2.CAP_PROP_FPS, fps)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        fourcc = (
            int(self.capture.get(cv2.CAP_PROP_FOURCC))
            .to_bytes(4, "little")
            .decode(errors="replace")
        )
        announced = self.capture.get(cv2.CAP_PROP_FPS)
        # DirectShow n'annonce pas d'images/s quand on ne les règle pas
        rate = f"{announced:.0f} fps" if announced > 0 else "fps non annoncé"
        print(
            f"{self.name} : {fourcc} {int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))}"
            f"x{int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))} {rate}"
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
