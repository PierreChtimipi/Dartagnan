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

Nouvelles volées enregistrées en direct par `tools/record_volleys.py` dans `data/captures/<jjmmaa-hhmm>-voleeN/` (exemple : `251126-1518-volee3`), au format de ce dossier ; sans zones tapées, la volée est gardée sans `points.txt`. Procédure de séance : [docs/test-detection.md](../docs/test-detection.md).

Les volées utiles sont ensuite copiées ici, une par dossier `<date>-serie<n>`.
