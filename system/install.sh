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
    git python3-venv python3-opencv python3-pygame v4l-utils dnsmasq-base

# Langue, clavier, fuseau horaire, nom d'hôte, pays Wi-Fi (requis pour le point d'accès)
raspi-config nonint do_change_locale fr_FR.UTF-8
raspi-config nonint do_configure_keyboard fr
raspi-config nonint do_change_timezone Europe/Paris
raspi-config nonint do_hostname dartagnan
raspi-config nonint do_wifi_country FR

# Ethernet : câble direct avec un PC, la Pi lui distribue une adresse et reste en 192.168.77.1
nmcli connection show dartagnan-eth >/dev/null 2>&1 \
    || nmcli connection add type ethernet ifname eth0 con-name dartagnan-eth
nmcli connection modify dartagnan-eth ipv4.method shared ipv4.addresses 192.168.77.1/24 \
    ipv6.method disabled connection.autoconnect yes connection.autoconnect-priority 100

# Point d'accès Wi-Fi de secours, activé par wifi-fallback.service (10.42.0.1).
# Mot de passe demandé une seule fois, conservé uniquement dans le profil NetworkManager.
if ! nmcli connection show dartagnan-ap >/dev/null 2>&1; then
    AP_PASSWORD="${AP_PASSWORD:-}"
    if [ -z "$AP_PASSWORD" ]; then
        read -rsp "Mot de passe du point d'accès Dartagnan (8 à 63 caractères) : " AP_PASSWORD
        echo
    fi
    [ "${#AP_PASSWORD}" -ge 8 ] && [ "${#AP_PASSWORD}" -le 63 ] \
        || { echo "Mot de passe invalide : 8 à 63 caractères." >&2; exit 1; }
    nmcli connection add type wifi ifname wlan0 con-name dartagnan-ap ssid Dartagnan \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$AP_PASSWORD"
fi
nmcli connection modify dartagnan-ap 802-11-wireless.mode ap 802-11-wireless.band bg \
    wifi-sec.proto rsn wifi-sec.pairwise ccmp wifi-sec.group ccmp \
    ipv4.method shared ipv4.addresses 10.42.0.1/24 ipv6.method disabled connection.autoconnect no

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

# Services démarrés au boot : application et point d'accès de secours
install -m 644 "$SYSTEM_DIR/dartagnan.service" "$SYSTEM_DIR/wifi-fallback.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable dartagnan.service wifi-fallback.service

echo "Installation terminée. Redémarrer : sudo reboot"
