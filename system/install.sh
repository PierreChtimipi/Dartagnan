#!/usr/bin/env bash
# Configuration de la Raspberry Pi pour Dartagnan.
# Rejouable : chaque exécution ramène le système au même état.
# Usage : sudo /opt/dartagnan/system/install.sh
set -euo pipefail

APP_USER=dartagnan
APP_DIR=/opt/dartagnan
DATA_DIR=/var/lib/dartagnan
SYSTEM_DIR="$(cd "$(dirname "$0")" && pwd)"
CMDLINE=/boot/firmware/cmdline.txt

[ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo." >&2; exit 1; }
[ "$SYSTEM_DIR" = "$APP_DIR/system" ] || { echo "Le dépôt doit être cloné dans $APP_DIR." >&2; exit 1; }
. /etc/os-release
[ "$VERSION_CODENAME" = trixie ] && [ "$(dpkg --print-architecture)" = arm64 ] \
    || { echo "Raspberry Pi OS Lite 64 bits (Trixie) attendue." >&2; exit 1; }

# Paquets : OpenCV et pygame viennent de l'OS, compilés pour la Pi
apt-get update
apt-get install -y --no-install-recommends \
    git python3-venv python3-opencv python3-pygame v4l-utils

# Langue, clavier, fuseau horaire, nom d'hôte
raspi-config nonint do_change_locale fr_FR.UTF-8
raspi-config nonint do_configure_keyboard fr
raspi-config nonint do_change_timezone Europe/Paris
raspi-config nonint do_hostname dartagnan

# Utilisateur : accès caméras (video), écran (render) et clavier ou boutons (input)
usermod -aG video,render,input "$APP_USER"

# SSH : les clés de system/authorized_keys remplacent les clés existantes,
# sauf si le fichier n'en contient aucune (évite de se fermer l'accès)
systemctl enable --now ssh
if grep -qv -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$SYSTEM_DIR/authorized_keys"; then
    install -d -m 700 -o "$APP_USER" -g "$APP_USER" "/home/$APP_USER/.ssh"
    install -m 600 -o "$APP_USER" -g "$APP_USER" "$SYSTEM_DIR/authorized_keys" "/home/$APP_USER/.ssh/authorized_keys"
fi

# Démarrage silencieux : pas de logo, de messages noyau ni de curseur sur l'écran
for arg in quiet loglevel=3 logo.nologo vt.global_cursor_default=0; do
    grep -qw -- "$arg" "$CMDLINE" || sed -i "1 s/\$/ $arg/" "$CMDLINE"
done

# Environnement Python : accès aux paquets de l'OS (OpenCV, pygame)
[ -d "$APP_DIR/.venv" ] || sudo -u "$APP_USER" python3 -m venv --system-site-packages "$APP_DIR/.venv"

# Données persistantes (calibration, configuration modifiée)
install -d -o "$APP_USER" -g "$APP_USER" "$DATA_DIR"

# Service de l'application, démarré au boot
install -m 644 "$SYSTEM_DIR/dartagnan.service" /etc/systemd/system/dartagnan.service
systemctl daemon-reload
systemctl enable dartagnan.service

echo "Installation terminée. Redémarrer : sudo reboot"
