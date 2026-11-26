# CLAUDE.md — Dartagnan

Comptage automatique des points sur une cible de fléchettes classique : 3 caméras USB, Raspberry Pi 4, Python + OpenCV, affichage pygame sur écran HDMI. Projet d'école d'équipe (JUNIA ISEN), dépôt partagé `PierreChtimipi/Dartagnan`.

**Le `README.md` est la référence du projet** (matériel, chaîne logicielle, géométrie de la cible, règles du 301, réseau, jalons). Ne pas dupliquer son contenu ici : le lire avant de coder, et le mettre à jour quand une décision change.

## État actuel

- Partie système : `system/` (installation de la Pi, services systemd, mise à jour) et `docs/installation.md`.
- Application MVP (section « Application » du README) : 301 solo ou à deux saisi aux boutons, comptes pseudo + PIN, historique, profil, calibration en maquette. Pas encore de caméras.
- Application fusionnée dans `main` (PR #4). Testée sur PC uniquement : 28 tests unitaires et parcours complet simulé.
- Calibration, fusionnée dans `main` (PR #5) : géométrie de la cible (`geometry/board.py`), passage image ↔ cible (`geometry/calibration.py`), acquisition partagée (`capture/camera.py`), calibration automatique (`geometry/auto_calibration.py`), outil de placement des points `tools/calibrate_board.py`. Vérifiés avec les caméras sur PC, pas encore sur la Pi.
- Simulation, fusionnée dans `main` (PR #6) : environnement de simulation `simulation/` (caméras virtuelles, images de synthèse) et prototype de détection (`detection/dart.py`, `geometry/triangulation.py`). Voir `simulation/README.md`. Photos réelles des trois caméras et zones réelles dans `photos/`, détection mesurée par `tools/detect_photos.py` : 47 zones justes sur 56 (voir `photos/README.md`).
- Branche `feat/enregistrement-volees` (pas encore fusionnée) : déclenchement à l'impact (`detection/trigger.py`) et enregistrement des volées avec affichage en direct, plein écran (`tools/record_volleys.py`). Séance d'essais : `docs/test-detection.md`. Première séance réelle sur PC le 2026-11-25 : 16 volées, versionnées dans `photos/`. Photo sans fléchette ignorée et cible vide vérifiée à l'Entrée : vérifiées sur les photos de la séance rejouées, pas encore avec les caméras.
- Prochain jalon : soutenance N°2 (1-2 déc. 2026) — détection, score 301 en solo, affichage temps réel.

## Décisions prises (ne pas remettre en cause sans l'utilisateur)

- **Interface** : décision finale de l'équipe, pygame plein écran sur l'écran HDMI de la Pi, piloté par trois boutons physiques. Pas d'application web, pas de saisie au téléphone.
- **Gestes sur Valider** : appui court = simple, deux appuis rapides = double, appui long = triple (dans les menus : valider, valider, retour). Dans les claviers à l'écran, deux appuis rapides tapent la touche deux fois.
- **Comptes** : pseudo + code PIN de 4 à 6 chiffres, pas de mot de passe ni d'OIDC. Le joueur 2 est choisi dans la liste **sans code** : choix assumé, même si n'importe qui peut ajouter une partie à l'historique d'un autre.
- **301** : sortie simple ou double out choisie au lancement de chaque partie. Saisie possible : 1 à 20, 25, Bull (compte comme un double) et Raté.
- **Profil** : parties jouées, victoires à deux, moyenne par volée (bust = 0), meilleure volée. Seules les parties finies comptent ; les parties abandonnées restent visibles dans l'historique.
- **Calibration** (écran de l'application) : maquette sans fonction, en attendant la chaîne caméras.
- **Développement de la détection** : sur PC, avec le hub et les 3 caméras branchés au PC. Vérification sur la Pi à chaque étape importante, sans commit (copie par `scp` ou VS Code Remote-SSH). Commit et push seulement une fois validé.
- **Calibration** (outil de développement) : 4 points par caméra sur le bord extérieur du double, aux limites 20|1, 6|10, 3|19, 11|14, puis homographie image → cible. Dimensions et ordre des secteurs uniquement dans `geometry/board.py`.
- **Simulation séparée de la réalité** : tout ce qui est de synthèse (caméras virtuelles, rendu, outil et tests de simulation) vit dans `simulation/` ; ses images dans `data/simulation/`, jamais dans `data/captures/` (photos réelles). Le code du jeu (`src/dartagnan/`) n'importe jamais `simulation/`. Règles, hypothèses et résultats dans `simulation/README.md`, à tenir à jour.
- **Détection prototypée** : méthode des droites projetées, retenue pour l'essai seulement (le choix définitif reste un point ouvert, à présenter à l'équipe). Toute modification se mesure avec `tools/detect_photos.py` sur toutes les séries de `photos/` : le nombre de zones justes ne doit pas baisser.
- **Photos de test versionnées** (décision de l'équipe, 2026-11-23) : séries réelles dans `photos/`, une par dossier avec `points.txt` ; volées de la séance du 2026-11-25 ajoutées le 2026-11-26 (environ 32 Mo au total). Les autres images restent hors de git (`data/`).
- **Calibration automatique** (`geometry/auto_calibration.py`) : hypothèses et usage dans le README. Si elle échoue sur de vraies images, régler d'abord les seuils HSV de `color_labels`, réglés sur deux photos seulement.
- **Boutons** : câblage pas encore décidé, simulés au clavier (`KEYS` dans `display/app.py`). Brancher les vrais boutons sur `Buttons.press` / `Buttons.release` sans toucher aux écrans.

## À vérifier ou à faire

- Premier lancement sur la vraie Pi : affichage KMS/DRM, police Montserrat et durcissement du service (`ProtectSystem=strict`, `ProtectHome=yes`) jamais testés. En cas d'échec : `journalctl -u dartagnan`.
- Logo : le « JUNIA simple blanc » du kit est un JPG blanc sur fond blanc, inutilisable. `display/assets/logo_junia_blanc.png` a été recréé en blanc à partir du logo violet officiel. Demander à l'école un PNG blanc officiel et le remplacer.
- Une partie en cours est perdue si la Pi s'éteint : elle n'est enregistrée qu'en quittant l'écran de fin (pour permettre la correction de la dernière fléchette) ou en abandonnant.
- Distorsion de l'objectif (100°) non corrigée : si la grille projetée par `calibrate_board.py` s'écarte des fils de la cible loin des 4 points, ajouter la calibration intrinsèque (damier).

## Passage du PC à la Pi : points à vérifier

Ce qui marche sur le PC n'est pas garanti sur la Pi. En cas d'écart, vérifier dans cet ordre :

- **Ouverture des caméras** : numéro DirectShow sur PC, `/dev/v4l/by-path` en V4L2 sur la Pi. Les points de calibration sont enregistrés dans l'ordre des sources, pas par port : vérifier que chaque caméra de `calibration.json` correspond à la bonne prise du hub, sinon refaire la calibration.
- **Format** : MJPEG forcé des deux côtés, mais pas dans le même ordre : sous DirectShow (PC), MJPEG n'est retenu qu'imposé après la résolution (sinon YUY2 à 8 img/s, et le troisième flux ne passe plus sur l'USB 2.0) ; sous V4L2 (Pi), avant la résolution. Contrôler la ligne affichée au lancement (`MJPG 1280x720`).
- **Réglages caméra** (exposition, gain, balance des blancs, netteté) : échelles différentes entre DirectShow et V4L2, valeurs non reportables telles quelles. Sur la Pi : `v4l2-ctl -d <chemin by-path> --list-ctrls`. Comparer une photo de la même scène prise sur chaque machine (touche P de `calibrate_board.py` sur PC). La calibration automatique dépend des couleurs : si elle échoue sur la Pi et pas sur PC, comparer d'abord la balance des blancs et l'exposition, puis les seuils HSV de `color_labels`.
- **Bande passante USB** : contrôleur différent. Trois flux validés sur la Pi en capture seule ; revérifier avec le traitement (erreur « No space left on device », images figées ou corrompues).
- **Performances** : à mesurer sur la Pi uniquement (images/s par flux, charge CPU avec `top`, latence impact → affichage). Le PC est beaucoup plus rapide : une détection fluide sur PC ne prouve rien. Calibration automatique : environ 1,5 s par image sur le PC de développement (photos de 800 et 2500 px), durée sur la Pi à mesurer.
- **Versions** : `opencv-python` et `numpy` de pip sur PC, paquets Debian sur la Pi (`dpkg-query -W python3-opencv python3-numpy`). Compilations différentes : résultats à recontrôler sur les mêmes images.
- **Affichage** : fenêtres OpenCV (`cv2.imshow`) sur PC seulement, la Pi n'a pas de bureau. Tout ce qui doit tourner sur la Pi affiche par pygame (KMS/DRM).
- **Calibration** : valable tant que caméras et cible ne bougent pas, à la même résolution (1280 × 720). Sur la Pi, le fichier va dans `/var/lib/dartagnan/calibration.json` (copie depuis le PC à confirmer).
- **Fichiers** : fins de ligne LF, bit exécutable des scripts (`git add --chmod=+x`), chemins Windows absents du code.

## Commandes

Sur PC, Python 3.13 : commandes du jeu, des tests et des outils caméra dans la section « Développement sur PC » du README, en PowerShell (Windows) et en sh (Linux, macOS). Sous Windows, PowerShell 5.1 refuse `&&` et `VAR=valeur commande` : une commande par ligne, variables par `$env:`. Test avec les caméras : `docs/test-calibration.md` (caméras, calibration), `docs/test-detection.md` (séance d'essais de la détection).

Syntaxe des scripts de la Pi (Git Bash ou Linux) : `bash -n system/*.sh`.

Une source peut aussi être une image ou une vidéo enregistrée (photos de `data/captures/`), pour travailler sans caméra.

Pour vérifier un écran sans l'ouvrir : `SDL_VIDEODRIVER=dummy`, dessiner l'écran sur une `pygame.Surface` de 1920 × 1080 et l'enregistrer avec `pygame.image.save`.

Le venv de développement doit être en Python 3.13 : pygame 2.6.1 ne s'installe pas avec Python 3.14 (pas de version précompilée). Si `python3.13` est absent, `uv python install 3.13`.

## Contraintes techniques (ne pas casser)

- **Cible** : Raspberry Pi OS Lite 64 bits Trixie (Debian 13), arm64, sans bureau. `install.sh` refuse tout autre système.
- **Dépendances** : OpenCV, pygame et Montserrat viennent des paquets apt (`python3-opencv`, `python3-pygame`, `fonts-montserrat`), **pas de pip** sur la Pi. Versions figées : celles de Trixie, reprises dans `requirements-dev.txt` pour le PC. Le venv `/opt/dartagnan/.venv` est créé avec `--system-site-packages`. Toute nouvelle dépendance passe d'abord par un paquet Debian dans `install.sh` ; en parler à l'équipe sinon.
- **Pas de Docker** ni de conteneurs dans le produit livré.
- **Affichage** : pygame en KMS/DRM direct (`SDL_VIDEODRIVER=kmsdrm`), 1920 × 1080.
- **Caméras** : toujours désignées par `/dev/v4l/by-path/...`, jamais `/dev/videoN`. Format MJPEG 1280 × 720 à 30 fps forcé (le YUY2 sature l'USB 2.0 du hub).
- **Performance** : CPU limité, détection seulement quand une fléchette vient de se planter. Objectif final : moins de 500 ms entre l'impact et l'affichage.
- **Détection** : traitement d'image classique, sans modèle entraîné.
- **Hors ligne** : le jeu fonctionne sans Internet ni service en ligne.
- **Chemins** : code dans `/opt/dartagnan` (clone du dépôt), données persistantes dans `/var/lib/dartagnan` (base `dartagnan.db` : comptes, parties ; plus tard la calibration). Dossier en 700, base en 600. Autre dossier via la variable `DARTAGNAN_DATA`.
- **`install.sh` doit rester rejouable** : chaque ajout doit être idempotent (tester l'existence avant de créer, `install`, `grep -q || ...`).
- **Fins de ligne LF** imposées (`.gitattributes`) : les scripts sont exécutés sur la Pi.

## Application

- Trois boutons seulement (Gauche, Droite, Valider) : toute nouvelle fonction doit rester utilisable ainsi. Les gestes sont décodés dans `display/buttons.py` (`Action.SINGLE` / `DOUBLE` / `TRIPLE`).
- Écrans dans `display/screens/` ; `MenuScreen` pour toute liste de choix. Tout est dessiné en 1920 × 1080 (`display/theme.py`).
- Charte JUNIA dans `theme.py` : violet dominant, orange pour la sélection, Montserrat. Le logo JUNIA ne s'affiche que sur fond violet, sans modification. Montserrat n'a pas de symboles (▶, ●, ⌫) : écrire en toutes lettres ou dessiner.
- Source de la charte : `kit_media_junia_2026/2025-2026 Charte JUNIA.pdf`, copie locale ignorée par git (52 Mo). Couleurs : violet `#3F2A56` et orange `#FF5C39` (institutionnelles), `#61CAD0`, `#2FAD66`, `#006880`, `#FFB9B5` (secondaires, par touches).
- Logique de jeu (`game/`) sans pygame ; base SQLite (`storage/`) uniquement en requêtes paramétrées.
- Sécurité : PIN haché (scrypt + sel), blocage après 5 essais, aucun secret en clair ni dans les journaux.

## Organisation du code

Arborescence proposée dans le README (`capture`, `detection`, `geometry`, `game`, `storage`, `display` sous `src/dartagnan/`, tests dans `tests/`), **encore à valider par l'équipe** : la suivre, mais signaler tout écart.

- Prévoir des sources caméra simulées (images ou vidéos enregistrées) dans `capture` pour développer et tester sans la Pi.
- Garder la logique pure (calcul du score, règles du jeu) indépendante d'OpenCV et de pygame, pour la tester sur PC.

## Décisions ouvertes : ne pas trancher seul

- From scratch ou réutilisation d'Autodarts (décision client).
- Raspberry Pi 4 ou 5.
- Méthode de détection de la pointe, câblage des boutons physiques (GPIO ou boîtier USB).

Si une tâche dépend de l'un de ces points, demander plutôt que supposer.

## Git et collaboration

- Dépôt d'équipe : une branche par sujet (`feat/...`, `docs/...`, `fix/...`), puis pull request vers `main`. Ne jamais pousser directement sur `main`.
- Messages de commit en français, style Conventional Commits : `feat: ...`, `docs: ...`, `chore: ...`, `fix: ...`.
- Documentation en français, phrases courtes, tableaux pour les références. Mettre à jour `README.md` et `docs/installation.md` en même temps que le code système concerné.

## Pi et réseau

- Les opérations sur la vraie Pi (SSH, flash, `install.sh`, `update.sh`, `nmcli`) sont faites par l'utilisateur : écrire ou corriger les guides, ne pas les lancer à sa place.
- Accès à la Pi : `dartagnan.local` (Wi-Fi), `192.168.77.1` (Ethernet direct), `10.42.0.1` (point d'accès `Dartagnan`).

## Secrets

- Jamais de mot de passe Wi-Fi ou de point d'accès dans le dépôt : ils vivent uniquement dans les profils NetworkManager de la Pi.
- `system/authorized_keys` ne contient que des clés **publiques** SSH.
