# Test de la détection avec les caméras

Séance d'essais sur le PC avec les trois caméras : chaque fléchette est photographiée automatiquement, sa zone détectée s'affiche en direct et la zone réelle est tapée au clavier. Les volées enregistrées servent ensuite à mesurer et améliorer la détection sans le matériel. Outil : `tools/record_volleys.py`, sur la branche `feat/enregistrement-volees` (puis `main` une fois fusionnée).

## Matériel

- caméras sur l'arceau au droit du 20, du 16 et du 15, hub USB branché sur le PC ;
- cible fixée, entièrement visible par les trois caméras ;
- éclairage constant pendant la séance : bandeau LED allumé s'il est installé, pas de lumière qui change en cours de route (fenêtre, plafonnier) ;
- caméras et cible immobiles pendant une séance : la calibration est faite une fois, au lancement de l'outil. Si l'une bouge, quitter et relancer.

## Préparation du PC

Dans PowerShell, depuis le dossier du dépôt :

```powershell
git fetch origin
git switch feat/enregistrement-volees
git pull
$env:PYTHONPATH="src"; $env:DARTAGNAN_DATA="data"
.venv\Scripts\python -m pytest
```

Attendu : `91 passed`. Les deux variables d'environnement sont à redonner dans chaque nouveau terminal. Installation de Python et du `.venv` : [test-calibration.md](test-calibration.md).

## Numéros des caméras

Windows numérote les caméras, webcam du PC comprise, et l'ordre peut changer d'un branchement à l'autre. À vérifier à chaque branchement du hub :

```powershell
.venv\Scripts\python tools\camera_preview.py 1 2 3
```

Passer la main devant chaque caméra et noter le numéro de celle du 20, du 16 et du 15. Attendu : `MJPG 1280x720` pour chaque caméra dans le terminal, environ 28 images par seconde par tuile à l'écran. Échap pour quitter. Problèmes d'ouverture ou de débit : [test-calibration.md](test-calibration.md).

## Lancement et calibration

Numéros dans l'ordre caméra du 20, du 16, du 15 (exemple avec `1 2 3`), angles `--top` dans le même ordre :

```powershell
.venv\Scripts\python tools\record_volleys.py 1 2 3 --top 180 54 306
```

L'outil s'ouvre en plein écran, Échap pour quitter. Avant de calibrer, vérifier les trois vues à gauche : cible entière et vide dans chaque image, débit proche de 28 img/s, personne dans le champ. Puis Entrée : `Calibration en cours…` pendant quelques secondes.

Calibration réussie :

- grille verte posée sur les fils de la cible dans chaque vue, côté opposé à la caméra compris ;
- écart de calibration affiché pour chaque caméra, en mm (refusé au-delà de 2 mm), ou `manuelle` (voir ci-dessous) ;
- `Volée 1` ouverte dans le panneau de droite.

`Caméra N : cible non trouvée` : vérifier que la cible est entière dans l'image, sans reflet ni ombre forte, et que l'ordre des numéros correspond à celui de `--top` ; Entrée pour réessayer.

Secours si la calibration automatique échoue toujours : Échap, placer les 4 points de cette caméra avec `tools/calibrate_board.py`, avec les mêmes numéros dans le même ordre ([test-calibration.md](test-calibration.md)), S pour enregistrer, Q, puis relancer `record_volleys.py`. Pour une caméra dont la calibration automatique échoue, les points de `data/calibration.json` sont repris : recalés sur les anneaux si possible (écart en mm affiché), sinon tels quels (`calibration manuelle`). Des points placés lors d'une séance précédente, caméras déplacées depuis, donnent une grille décalée : toujours vérifier la grille.

## Mouvement au repos

Le panneau de droite affiche `Mouvement` : part de la cible qui change d'une image à la suivante. Une photo est prise quand ce mouvement dépasse 0,2 % (une fléchette arrive), puis reste sous 0,05 % pendant 10 images (environ 0,35 s). Au repos, la valeur doit rester sous 0,05 %, idéalement à 0,00 %. Au-dessus (scintillement de l'éclairage, bruit des caméras), aucune photo n'est prise : noter la valeur. Les seuils se règlent dans `ImpactTrigger` (`src/dartagnan/detection/trigger.py`).

## Déroulement d'une volée

| Moment | Action | À l'écran |
|---|---|---|
| Fléchette lancée ou plantée | sortir la main du champ, attendre | `Mouvement…`, puis photo : impact numéroté sur la cible du centre, droite de chaque caméra, zone détectée à droite |
| Fléchette suivante | seulement après l'affichage de la précédente | |
| Trois fléchettes photographiées | taper les zones réelles dans l'ordre (`20 T19 D5`, `25`, `Bull`, `Out`), retirer les fléchettes, sortir du champ, Entrée | impacts en vert si la zone tapée correspond, en rouge sinon ; Entrée ouvre la volée suivante sur une nouvelle photo de la cible vide, ou affiche `Cible pas vide (caméras …)` si deux caméras ou plus voient encore une fléchette ou une ombre |
| Photo sans changement de la taille d'une fléchette dans aucune caméra | rien | `Photo ignorée`, la fléchette suivante reste attendue |
| Photo d'autre chose qu'une nouvelle fléchette (main, ombre, fléchette tombée) | Suppr | photo et fléchette supprimées |
| Fléchette hors de la cible, sans photo | ne pas taper sa zone | |
| Fin de séance | Échap | zones de la volée en cours enregistrées si complètes, volée vide supprimée |

Une zone par photo, dans l'ordre des photos. Une fléchette sur un fil se note dans la zone où la pointe est entrée. Retour arrière corrige la saisie. Le bilan `Séance : justes / total` se met à jour à chaque Entrée.

Chaque volée est rangée dans `data/captures/<jjmmaa-hhmm>-voleeN/` : pour chaque caméra, photo de la cible vide puis une photo par fléchette, et `points.txt` avec les zones tapées.

## Quoi lancer

Une vingtaine de volées variées, à adapter au temps disponible :

- toutes les régions de la cible, en particulier celles éloignées de chaque caméra ;
- simples, doubles, triples, 25 et Bull ;
- fléchettes sur ou près d'un fil ;
- fléchettes groupées dans un même secteur, qui se masquent (cas raté de la série 1) ;
- fléchettes sur des secteurs noirs (fût noir peu visible) ;
- une ou deux fléchettes dans la couronne noire, hors du double (`Out`).

Cible posée à plat : planter chaque fléchette sans toucher les autres, retirer la main lentement.

## À relever pendant la séance

| | Caméra du 20 | Caméra du 16 | Caméra du 15 |
|---|---|---|---|
| Numéro Windows | | | |
| Images par seconde | | | |
| Écart de calibration (mm) | | | |
| Grille sur les fils, côté opposé compris ? | | | |
| Fléchettes sans axe (`Pas d'axe…`), et où | | | |

Pour la séance : `Mouvement` au repos, fléchettes non photographiées, fausses alertes, bilan `Séance` final, écart entre droites habituel (affiché sous chaque fléchette), fixation de la cible (mur ou à plat), éclairage, modèle du PC.

## Après la séance

Mesure sur toutes les volées enregistrées avec leurs zones :

```powershell
.venv\Scripts\python tools\detect_photos.py (Get-ChildItem data\captures\*-volee*\points.txt).Directory.FullName
```

Résultat dans `data/detection/resultats.md`, avec les images de chaque fléchette. Chaque volée y est recalibrée sur sa propre photo vide : le résultat peut différer légèrement du bilan affiché en direct.

Les volées restent dans `data/captures/`, hors de git (environ 1,5 Mo par volée). Quelques volées représentatives peuvent être copiées dans `photos/`, une par dossier `<date>-serie<n>`, après accord de l'équipe sur la taille.

## Problèmes fréquents

| Symptôme | Cause probable | À faire |
|---|---|---|
| `Mouvement…` affiché en permanence | mouvement au repos au-dessus de 0,05 % | noter la valeur au repos |
| Fléchette plantée, aucune photo | mouvement à l'arrivée sous 0,2 % | noter la valeur la plus haute vue à l'arrivée |
| Fausses alertes fréquentes | exposition automatique quand quelqu'un approche, ombres | Suppr, noter les circonstances |
| `Cible pas vide` alors que la cible est vide et personne autour | photo vide de la volée prise avec une fléchette ou une ombre (calibration comprise) | Échap, relancer l'outil |
| Vue figée ou débit bas | bande passante USB | autre port du PC |
| `Zone invalide` ou `N zones attendues` | saisie | Retour arrière, une zone par photo |
