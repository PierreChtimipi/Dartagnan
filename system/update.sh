#!/usr/bin/env bash
# Mise à jour du jeu : dernière version de main, réinstallation, redémarrage. Internet requis.
# Usage : sudo /opt/dartagnan/system/update.sh
set -euo pipefail

APP_USER=dartagnan
APP_DIR=/opt/dartagnan

[ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo." >&2; exit 1; }

# Échoue sans rien écraser si des modifications locales existent
sudo -u "$APP_USER" git -C "$APP_DIR" switch main
sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only origin main

"$APP_DIR/system/install.sh"
systemctl restart dartagnan.service
echo "Mise à jour terminée."
