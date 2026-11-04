# Installation de la Raspberry Pi

Préparation de la carte SD, connexion à la Pi et configuration du système pour Dartagnan.

## Matériel nécessaire

- Raspberry Pi 4 et son alimentation officielle 5 V 3 A USB-C.
- Carte microSD de 16 Go ou plus et un lecteur de carte sur le PC.
- Raspberry Pi Imager, à télécharger sur raspberrypi.com/software.
- Un réseau Wi-Fi avec accès Internet, nom (SSID) et mot de passe notés exactement (majuscules, espaces, accents).

## Réseau Wi-Fi à utiliser

La Pi a besoin d'un Wi-Fi avec Internet pour l'installation et les mises à jour du jeu. Le réseau doit être protégé par un simple mot de passe (WPA2 ou WPA3 personnel), **sans portail captif** : une Pi sans écran ne peut pas remplir une page de connexion.

| Contexte | Réseau | Remarque |
|---|---|---|
| Chez le client | Wi-Fi de la box du domicile | Cas normal, aucune contrainte |
| En développement | Partage de connexion d'un téléphone | Exemple utilisé par l'équipe |
| À l'école | Non utilisable | Portail captif, enregistrement d'adresse MAC impossible |

Sur iPhone, activer « Maximiser la compatibilité » dans le partage de connexion si la Pi ne s'y connecte pas (force le 2,4 GHz).

## Préparation de la carte SD avec Raspberry Pi Imager

Insérer la carte SD dans le PC, lancer Raspberry Pi Imager et renseigner chaque onglet, puis « Next ».

| Onglet | Réglage |
|---|---|
| Device | Raspberry Pi 4 |
| OS | Raspberry Pi OS (other), puis Raspberry Pi OS Lite (64-bit). Ne pas prendre la version avec bureau proposée en premier. |
| Storage | La carte SD (vérifier sa taille pour ne pas effacer un autre disque), « Exclude system drives » coché |
| Customisation | À remplir entièrement, ne pas choisir « Skip customisation » |
| Writing | Relire le récapitulatif, « Write », puis « I understand, erase and write ». Accepter la demande administrateur de Windows et laisser la vérification aller au bout. « Finish » à la fin. |

Sous-onglets de Customisation :

| Sous-onglet | Valeur |
|---|---|
| Hostname | `dartagnan` |
| Localisation | Capitale : Paris. Vérifier le fuseau `Europe/Paris` et le clavier `fr`. Ce choix règle aussi le pays du Wi-Fi. |
| User | Nom d'utilisateur `dartagnan` (minuscules), mot de passe à noter : il sert pour SSH et pour `sudo` |
| Wi-Fi | Réseau sécurisé. SSID et mot de passe du Wi-Fi choisi (box du domicile, ou partage de connexion en développement). Imager pré-remplit souvent le Wi-Fi du PC : le remplacer si besoin. « Hidden SSID » décoché. |
| Remote Access | « Enable SSH » activé, « Use password authentication » |
| Raspberry Pi Connect | Désactivé (service en ligne non utilisé) |

Ne pas choisir « Use public key authentication » : cette option désactive la connexion par mot de passe. Les clés SSH de l'équipe sont installées ensuite par `install.sh` depuis `system/authorized_keys`, et le mot de passe reste un accès de secours.

Dans « App Options » (en bas à gauche) : désactiver « Enable anonymous statistics telemetry », puis « Save ».

## Premier démarrage

- Insérer la carte SD dans la Pi, brancher les caméras, puis l'alimentation.
- Le Wi-Fi configuré dans Imager doit être actif, et le PC connecté au même réseau.
- Attendre 2 à 3 minutes : au premier démarrage, la Pi agrandit sa partition et redémarre une fois.

## Connexion à la Pi

SSH est inclus dans Windows : les commandes `ssh` se tapent dans PowerShell. Le mot de passe demandé est celui de l'onglet User d'Imager.

| Accès | Disponible | Commande |
|---|---|---|
| Wi-Fi configuré dans Imager (domicile ou partage de connexion) | Dès le premier démarrage | `ssh dartagnan@dartagnan.local` |
| Câble Ethernet direct entre le PC et la Pi | Après `install.sh` | `ssh dartagnan@192.168.77.1` |
| Point d'accès Wi-Fi `Dartagnan` créé par la Pi | Après `install.sh`, si aucun Wi-Fi connu n'est connecté 45 s après le démarrage | Connecter le PC au Wi-Fi `Dartagnan`, puis `ssh dartagnan@10.42.0.1` |
| Écran HDMI et clavier USB branchés sur la Pi | Toujours, tant que le jeu n'occupe pas l'écran (à confirmer une fois le jeu en place) | Connexion directe avec l'utilisateur `dartagnan` |

Si `dartagnan.local` ne répond pas, utiliser l'adresse IP de la Pi :

- box du domicile : liste des appareils connectés dans l'interface de la box ;
- partage de connexion Android : liste des appareils connectés ;
- sinon : `arp -a` dans PowerShell, puis essayer les adresses du réseau.

Après un nouveau flash de la carte, SSH refuse la connexion car la clé de la Pi a changé. Sur le PC :

```sh
ssh-keygen -R dartagnan.local
```

## Installation du projet

En SSH sur la Pi, avec Internet :

```sh
sudo apt-get update && sudo apt-get install -y git
sudo install -d -o dartagnan -g dartagnan /opt/dartagnan
git clone https://github.com/PierreChtimipi/Dartagnan.git /opt/dartagnan
sudo /opt/dartagnan/system/install.sh
sudo reboot
```

Au premier lancement, `install.sh` demande le mot de passe du point d'accès `Dartagnan` (8 à 63 caractères, rien ne s'affiche pendant la saisie). Le noter : il sert à joindre la Pi sans réseau.

`install.sh` règle la langue, le clavier, le fuseau horaire, les accès réseau et les clés SSH, installe OpenCV et pygame, et active le démarrage automatique du jeu. Il peut être relancé sans risque.

## Vérifications

Après le redémarrage, en SSH :

```sh
groups                                  # doit contenir video render input
ls -l /dev/v4l/by-path/                 # une entrée par caméra branchée
nmcli connection show                   # dartagnan-eth, dartagnan-ap et le Wi-Fi configuré
python3 -c "import cv2; print(cv2.__version__)"
```

Test de l'écran HDMI (micro-HDMI 0, à côté de l'alimentation) : l'écran doit devenir blanc 3 secondes et la commande afficher `(1920, 1080)`.

```sh
/opt/dartagnan/.venv/bin/python -c "import os, time, pygame; os.environ['SDL_VIDEODRIVER']='kmsdrm'; pygame.display.init(); s=pygame.display.set_mode((0,0), pygame.FULLSCREEN); print(s.get_size()); s.fill((255,255,255)); pygame.display.flip(); time.sleep(3)"
```

## Configuration réseau sur la Pi

- La Pi mémorise plusieurs Wi-Fi et se connecte au premier connu à portée. Ajouter un Wi-Fi (partage de connexion d'un autre membre de l'équipe, autre domicile), même s'il n'est pas à portée, sans couper la connexion en cours :

  ```sh
  sudo nmcli connection add type wifi ifname wlan0 con-name "<nom>" ssid "<SSID>" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<mot de passe>"
  ```

- Lister les Wi-Fi mémorisés : `nmcli connection show`. En supprimer un : `sudo nmcli connection delete "<nom>"`.
- Un membre de l'équipe dont le Wi-Fi n'est pas encore mémorisé se connecte par le point d'accès `Dartagnan` ou le câble Ethernet pour l'ajouter. Les mots de passe Wi-Fi ne vont jamais dans le dépôt.
- Changer le mot de passe du point d'accès : `sudo nmcli connection modify dartagnan-ap wifi-sec.psk "<nouveau>"`.
- Revenir sur un Wi-Fi connu quand le point d'accès est actif : redémarrer la Pi à portée de ce Wi-Fi.
- Le port Ethernet est réservé au câble direct avec un PC : la Pi y distribue des adresses. Ne pas le brancher sur une box ou un réseau existant.

## Maintenance

- Mise à jour du jeu, Internet requis : `sudo /opt/dartagnan/system/update.sh` récupère la dernière version de `main`, relance `install.sh` et redémarre le jeu.
- Donner l'accès SSH par clé à un membre de l'équipe : ajouter sa clé publique dans `system/authorized_keys` (une par ligne), puis relancer `install.sh` ou `update.sh`.
