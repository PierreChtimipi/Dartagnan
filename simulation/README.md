# Calibration et détection en simulation

Travail théorique mené avant l'arrivée des caméras : calibration de la cible et détection des fléchettes développées et mesurées sur des images, photos réelles et vues de synthèse. Tout tourne sur un PC, sans matériel.

Les résultats valent pour des images idéales. Ils montrent que la méthode tient ; la précision réelle reste à mesurer avec les caméras, l'éclairage et la cible du projet.

## Séparation entre simulation et réalité

| | Réalité | Simulation |
|---|---|---|
| Code | `src/dartagnan/`, `tools/` | `simulation/` (ce dossier) |
| Images | `data/captures/` : photos de vraies cibles et des caméras | `data/simulation/` : vues de synthèse générées |
| Tests | `tests/` | `simulation/test_simulation.py` |
| Branche | `feat/calibration-cible` | `feat/simulation` |

- Le code du jeu (`src/dartagnan/`) ne dépend jamais de ce dossier ; la simulation utilise le code du jeu tel quel.
- Aucune image de synthèse dans `data/captures/`, aucune photo réelle dans `data/simulation/`.
- Un résultat obtenu ici est toujours présenté comme « en simulation », jamais comme mesuré sur le matériel.
- La détection par droites projetées (`src/dartagnan/detection/dart.py`, `src/dartagnan/geometry/triangulation.py`) n'a été validée qu'ici : elle reste dans la branche `feat/simulation` tant qu'elle n'a pas été essayée avec les caméras et retenue par l'équipe.

## Hypothèses de la simulation

Trois caméras virtuelles, au droit du 20, du 16 et du 15, visées vers le centre de la cible :

| Paramètre | Valeur retenue |
|---|---|
| Distance au centre de la cible | 250 mm |
| Hauteur devant la surface de la cible | 60 mm (vue rasante, environ 14°) |
| Caméra | OV9732, 1280 × 720, champ de 100° (en diagonale, à confirmer) |
| Objectif | sans distorsion |
| Cible | dimensions réglementaires du README, rouge et verte, 20 en rouge |

La position des caméras est une hypothèse, à remplacer par celle de l'arceau une fois conçu. Distance et hauteur se règlent à chaque lancement de la simulation.

## Calibration de chaque caméra

La calibration relie chaque pixel de l'image d'une caméra à une position en millimètres sur la cible. Une calibration par caméra, valable tant que la caméra et la cible ne bougent pas.

**Manuelle** : quatre points cliqués sur le bord extérieur du double, aux limites 20|1, 6|10, 3|19 et 11|14. La grille de la cible est alors superposée à l'image pour contrôle visuel, et la zone visée par la souris s'affiche (T20, D5, Bull).

**Automatique**, par traitement d'image classique, sans apprentissage :

- les anneaux double et triple et le bull sont repérés par leurs couleurs rouge et verte ;
- la forme de l'anneau double et la position du bull donnent la perspective ;
- les bords des anneaux, mesurés sur plus d'un millier de points, sont ajustés à leurs rayons réels ;
- l'alternance rouge / vert d'un secteur à l'autre donne l'orientation de la cible.

Sans aucun clic, la calibration automatique a besoin de connaître approximativement l'orientation de chaque caméra (à 18° près). À partir de quatre clics approximatifs, elle les recale seule.

## Détection d'une fléchette

Méthode des droites projetées, prototypée pour l'essai. Le choix de la méthode de détection reste un point ouvert du projet, à valider avec l'équipe.

- Chaque caméra compare l'image d'avant et d'après le lancer : les pixels qui ont changé sont ceux de la nouvelle fléchette, dont on ajuste l'axe.
- La calibration ramène cet axe sur le plan de la cible : on obtient une droite qui passe par la pointe.
- Les droites des trois caméras se coupent à la pointe. La position est trouvée même si la pointe est cachée dans une vue.
- Le score est calculé à partir de cette position.

Un changement qui couvre une grande partie de l'image (lumière, passage d'un joueur) est ignoré.

## Résultats

Mesures sur le PC de développement, Windows 11, Python 3.13 (processeur à confirmer).

**Calibration automatique sur deux photos de cibles du commerce**, sans clic :

| Photo | Écart moyen bords mesurés / modèle | Durée |
|---|---|---|
| Cible de face, 2500 × 2500 px | 0,76 mm | 1,2 à 1,5 s |
| Cible de biais, 800 × 800 px | 1,35 mm | 1,2 à 1,5 s |

Pas de position de référence sur ces photos : l'écart mesure l'accord entre les bords détectés et le modèle de la cible, pas l'erreur réelle. Contrôle visuel : grille superposée aux fils de la cible.

**Chaîne complète sur vues de synthèse** (calibration automatique des trois caméras, puis volées de trois fléchettes) :

| Hauteur des caméras | Erreur de calibration (max) | Zones justes | Erreur moyenne sur la pointe | Erreur max |
|---|---|---|---|---|
| 60 mm (hypothèse retenue) | 0,3 mm | 59 sur 60 | 0,6 mm | 3,2 mm |
| 120 mm | 0,4 mm | 29 sur 30 | 1,4 mm | 5,0 mm |
| 30 mm | sans clic : en échec ; depuis quatre clics approximatifs : 1,5 mm | non mesuré | non mesuré | non mesuré |

Le seul écart à 60 mm est une fléchette plantée à moins de 0,5 mm de la limite intérieure du double, comptée en double au lieu de simple.

## Limites et points à valider avec le matériel

- Images de synthèse idéales : ni distorsion de l'objectif grand angle, ni flou, ni compression MJPEG, ni ombres, ni reflets. Ces effets dégraderont la précision.
- Couleurs : seuils de détection du rouge et du vert réglés sur deux photos seulement, à ajuster avec les caméras et l'éclairage LED.
- Vue très rasante (caméras à 30 mm environ de la cible) : calibration automatique sans clic en échec.
- Distorsion de l'objectif de 100° : sera probablement à corriger par une calibration de l'objectif (mire en damier).
- Durée sur la Raspberry Pi 4 : non mesurée. La calibration est ponctuelle ; la détection devra tenir l'objectif de 500 ms entre l'impact et l'affichage.
- Dimensions de la cible du projet : à relever, certaines cibles du commerce s'écartent des dimensions réglementaires.
- Simulation à compléter : distorsion de l'objectif, flou et compression MJPEG, ombres des fléchettes, éclairage LED, fléchettes qui se masquent entre elles.

## Reproduire

Depuis le dossier du projet, environnement de développement installé (voir « Développement sur PC » dans le README) :

```sh
DARTAGNAN_DATA=data PYTHONPATH=src .venv/Scripts/python simulation/simulate_throws.py --volleys 10 --save 3
DARTAGNAN_DATA=data PYTHONPATH=src .venv/Scripts/python tools/calibrate_board.py data/captures/<photo>.jpg
.venv/Scripts/python -m pytest simulation
```

La position des caméras virtuelles se change dans les constantes de `synthetic.py` ou par les options `--distance` et `--height`.

La simulation enregistre une image par volée dans `data/simulation/` : les trois vues des caméras avec l'axe détecté de chaque fléchette, et la cible de face avec les droites, la position réelle et la position détectée. Options `--height` et `--distance` pour une autre position des caméras.
