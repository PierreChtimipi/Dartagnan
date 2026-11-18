# Test des caméras et de la calibration

Vérification, sur la branche `feat/calibration-cible`, des trois caméras sur le PC puis sur la Pi, et de la calibration manuelle et automatique de la cible. Les résultats sont à relever dans le tableau en fin de document.

## Prérequis

Matériel :

- les trois caméras branchées sur le hub USB, fixées dans leur position définitive autour de la cible : une calibration n'est valable que tant que caméras et cible ne bougent plus ;
- la cible accrochée, sans fléchette, éclairage LED allumé ;
- le hub branché sur le PC Windows (puis sur la Pi pour la dernière partie).

Logiciel, dans PowerShell depuis le dossier du dépôt :

```powershell
git fetch origin
git switch feat/calibration-cible
git pull
```

Si Python 3.13 ou l'environnement `.venv` manquent :

```powershell
py install 3.13
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

À chaque nouveau terminal :

```powershell
$env:PYTHONPATH="src"; $env:DARTAGNAN_DATA="data"
```

Tests unitaires, sans caméra :

```powershell
.venv\Scripts\python -m pytest
```

Attendu : `55 passed`, aucun `failed`.

## Caméras sur le PC

Windows numérote les caméras `0`, `1`, `2`… La webcam intégrée du PC occupe en général un de ces numéros (souvent `0`, à confirmer), et l'ordre peut changer d'un branchement à l'autre.

```powershell
.venv\Scripts\python tools\camera_preview.py 1 2 3
```

À observer :

- dans le terminal, une ligne par caméra, par exemple `1 : MJPG 1280x720 30 fps` (DirectShow peut annoncer un format inexact) ;
- à l'écran, une mosaïque plein écran avec une tuile par caméra, son numéro et son débit en images par seconde, attendu proche de 30 (à confirmer sur PC) ;
- Échap ou Q pour quitter.

Passer la main devant chaque caméra pour savoir quel numéro correspond à la caméra au droit du 20, du 16 et du 15. Les noter : la suite en dépend.

En cas de problème :

- `Ouverture impossible : N` : numéro inexistant, ou caméra déjà utilisée par une autre application (Teams, application Caméra) ;
- la webcam du PC apparaît dans la mosaïque : retirer son numéro de la commande ;
- tuile noire ou débit proche de 0 : bande passante USB, essayer un autre port du PC ou deux caméras seulement.

## Calibration

Les numéros sont donnés dans l'ordre caméra du 20, du 16, du 15 (exemple avec `1 2 3`) :

```powershell
.venv\Scripts\python tools\calibrate_board.py 1 2 3 --top 180 54 306
```

`--top` donne, pour chaque caméra et dans le même ordre, l'angle de la cible visible en haut de l'image, en degrés dans le sens horaire depuis le 20 (20 = 0, 6 = 90, 3 = 180, 11 = 270 ; 18° par secteur). Caméra au droit du 20 visée vers le centre : 180 ; du 16 : 54 ; du 15 : 306. Une précision de 18° suffit.

Une caméra est affichée à la fois. Touches : A détection automatique, Tab caméra suivante, R efface les points, P photo de chaque caméra, S enregistre, Q quitte. La fenêtre se redimensionne à la souris.

**Calibration automatique** : touche A sur chaque caméra.

- Attendu : quatre points jaunes placés et la grille verte de la cible superposée à l'image ; dans le terminal, `<caméra> : cible détectée, écart moyen X mm sur N points`.
- Valeurs indicatives, mesurées sur deux photos de cibles du commerce et non avec ces caméras : écart moyen de 0,8 à 1,4 mm, de 1 000 à 1 400 points.
- `cible non trouvée`, ou grille tournée (numéros décalés) : cliquer les quatre points demandés, même approximativement, sur le bord extérieur du double aux limites 20|1, 6|10, 3|19 et 11|14, puis A.

**Calibration manuelle**, si l'automatique échoue : cliquer les quatre points demandés, puis faire glisser chaque point jusqu'à ce que la grille colle aux fils.

**Contrôle**, pour chaque caméra :

- la grille suit les fils sur toute la cible, y compris du côté opposé à la caméra ;
- en survolant à la souris le triple 20, le double 16, le bull et un simple 3, l'étiquette affichée correspond à la zone ;
- grille juste près des quatre points mais décalée ailleurs : déformation de l'objectif grand angle, attendue, à noter avec l'endroit et l'écart estimé.

**Enregistrement** : S écrit `data/calibration.json`. Relancer l'outil avec les mêmes numéros reprend les points.

**Photos pour la suite** : P enregistre une image de chaque caméra dans `data/captures/`. Prendre une série : cible vide, puis une, deux et trois fléchettes plantées. Elles servent à régler la détection sans les caméras. Ne pas les ajouter à git.

## Caméras sur la Pi

Hub branché sur la Pi, en SSH avec l'utilisateur `dartagnan`. Le jeu tourne en service et occupe l'écran : l'arrêter le temps du test.

```sh
sudo systemctl stop dartagnan
git -C /opt/dartagnan fetch origin
git -C /opt/dartagnan switch feat/calibration-cible
ls -l /dev/v4l/by-path/
cd /opt/dartagnan
PYTHONPATH=src SDL_VIDEODRIVER=kmsdrm .venv/bin/python tools/camera_preview.py
vcgencmd get_throttled
```

À observer :

- `ls` liste les entrées `...-usb-...-video-index0`, une par caméra ;
- une ligne `... : MJPG 1280x720 30 fps` par caméra, et la mosaïque sur l'écran HDMI à environ 30 images par seconde par tuile (déjà validé le 13/11 avec le même affichage) ;
- `throttled=0x0` : pas de sous-tension.

L'outil de calibration ne fonctionne pas sur la Pi, qui n'a pas de bureau. Une calibration faite sur le PC reste valable si caméras et cible n'ont pas bougé, mais l'ordre des caméras diffère (numéros Windows sur PC, ports `by-path` sur la Pi) : son usage sur la Pi est à confirmer. Les autres écarts possibles entre PC et Pi sont listés dans la section « Passage du PC à la Pi » de `CLAUDE.md`.

Pour remettre la Pi sur la version principale et relancer le jeu, Internet requis :

```sh
sudo /opt/dartagnan/system/update.sh
```

## Résultats à relever

| | Caméra du 20 | Caméra du 16 | Caméra du 15 |
|---|---|---|---|
| Numéro Windows | | | |
| Format annoncé sur PC | | | |
| Images par seconde, PC | | | |
| Images par seconde, Pi | | | |
| Touche A sans clic : réussie ? | | | |
| Écart moyen (mm) et nombre de points | | | |
| Grille juste côté opposé ? | | | |
| Survol T20, D16, bull, 3 justes ? | | | |
| Remarques (décalages, reflets, couleurs) | | | |

À noter aussi : modèle du PC et processeur (pour les mesures de durée), éclairage pendant le test, liste des photos prises avec la touche P.
