# Photos réelles de test

Séries de photos des trois caméras du projet, avec la zone réelle de chaque fléchette, pour développer et mesurer la détection sans la cible ni les caméras. Images versionnées par décision de l'équipe (environ 5 Mo) ; aucune image de synthèse ici, elles vont dans `simulation/`.

## Contenu d'une série

Un dossier par série, nommé `<date>-serie<n>` :

- `camN_<horodatage>.jpg` : photo de la caméra N (1 au droit du 20, 2 au droit du 16, 3 au droit du 15), 1280 × 720, prise avec la touche P de `tools/calibrate_board.py` ;
- par caméra, dans l'ordre des horodatages : cible vide, puis une fléchette de plus à chaque photo ;
- `points.txt` : zone réelle de chaque fléchette, une par ligne, dans l'ordre (`20`, `T19`, `D5`, `25`, `Bull`, `Out`).

Cible posée à plat, caméras sur l'arceau provisoire, éclairage de la salle.

| Série | Zones réelles | Particularité |
|---|---|---|
| `2026-11-19-serie1` | 20, 20, 25 | fléchettes groupées au centre ; photo vide des caméras 2 et 3 prise juste avant la série 2, cible inchangée |
| `2026-11-19-serie2` | 16, 16, 13 | |
| `2026-11-19-serie3` | 17, 16, 8 | |

## Mesurer la détection

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python tools\detect_photos.py photos\2026-11-19-serie1 photos\2026-11-19-serie2 photos\2026-11-19-serie3
```

Pour chaque série : calibration automatique de chaque caméra sur sa photo vide, détection de chaque fléchette, comparaison avec `points.txt`. Le terminal affiche le tableau réel / détecté et le nombre de zones justes. Dans `data/detection/` : grille de calibration des trois caméras, axe repéré par chaque caméra pour chaque fléchette, vue de face avec les positions détectées (vert si juste, rouge sinon), `resultats.md`.

Résultat de référence (prototype des droites projetées, PC de développement) : 5 zones justes sur 9. Série 3 entièrement juste, droites des trois caméras concordantes à 1 mm près. Série 1 fausse : fléchettes groupées qui se masquent ou bougent quand on plante la suivante, fûts noirs peu visibles sur les secteurs noirs, fléchette éloignée d'une caméra qui dépasse du masque de la cible.

Une amélioration de la détection se juge en relançant la commande sur toutes les séries : le nombre de zones justes doit augmenter sans faire baisser celles déjà justes.

## Ajouter une série

Enregistrement en direct, caméras et cible fixes :

```powershell
$env:PYTHONPATH="src"; $env:DARTAGNAN_DATA="data"
.venv\Scripts\python tools\record_volleys.py 1 2 3 --top 180 54 306
```

Plein écran en 1920 × 1080 : les trois caméras à gauche (grille de la cible calibrée, axe de la dernière fléchette), au centre une cible de face avec la droite projetée par chaque caméra et les impacts, à droite la volée en cours, les zones détectées et le bilan de la séance. Impact en vert si la zone réelle tapée correspond, en rouge sinon.

| Moment | Action |
|---|---|
| Cible vide, personne devant | Entrée : calibration des trois caméras, première volée |
| Fléchette plantée | photo automatique quand l'image redevient stable, zone détectée affichée (3 par volée) |
| Fausse alerte (main, fléchette tombée) | Suppr : photos et fléchette supprimées |
| Fin de volée | taper les zones réelles dans l'ordre (`20 T19 D5`, `25`, `Bull`, `Out`), une par photo, retirer les fléchettes, Entrée |
| Fin de séance | Échap : zones de la dernière volée enregistrées si complètes |

Chaque volée va dans `data/captures/<jjmmaa-hhmm>-voleeN/` (exemple : `251126-1518-volee3`, numéros à la suite dans la journée), au format de ce dossier. Sans zones tapées, la volée est gardée sans `points.txt`.

Limites : une fléchette hors de la cible (mur, arceau) ne déclenche rien, ne pas taper sa zone ; deux fléchettes lancées sans que l'image se stabilise entre elles donnent une seule photo.

Les volées utiles sont ensuite copiées ici, une par dossier `<date>-serie<n>`.
