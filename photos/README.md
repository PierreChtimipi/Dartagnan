# Photos réelles de test

Séries de photos des trois caméras du projet, avec la zone réelle de chaque fléchette, pour développer et mesurer la détection sans la cible ni les caméras. Images versionnées par décision de l'équipe (environ 32 Mo) ; aucune image de synthèse ici, elles vont dans `simulation/`.

## Contenu d'une série

Un dossier par série :

- `<date>-serie<n>` : photos prises avec la touche P de `tools/calibrate_board.py` ;
- `<date>-volee<n>` : volée enregistrée en direct par `tools/record_volleys.py`, numéro de la volée dans la séance.

Dans chaque dossier :

- `camN_<horodatage>.jpg` : photo de la caméra N (1 au droit du 20, 2 au droit du 16, 3 au droit du 15), 1280 × 720 ;
- par caméra, dans l'ordre des horodatages : cible vide, puis une fléchette de plus à chaque photo ;
- `points.txt` : zone réelle de chaque fléchette, une par ligne, dans l'ordre (`20`, `T19`, `D5`, `25`, `Bull`, `Out`).

Cible posée à plat, caméras sur l'arceau provisoire, éclairage de la salle.

| Série | Zones réelles | Particularité |
|---|---|---|
| `2026-11-19-serie1` | 20, 20, 25 | fléchettes groupées au centre ; photo vide des caméras 2 et 3 prise juste avant la série 2, cible inchangée |
| `2026-11-19-serie2` | 16, 16, 13 | |
| `2026-11-19-serie3` | 17, 16, 8 | |
| `2026-11-25-volee1` | 9, T3, 12 | |
| `2026-11-25-volee2` | 7, 12, 16 | photo vide prise avec les 3 fléchettes de la volée 1 encore plantées ; 12 sur le fil avec le 9 |
| `2026-11-25-volee3` | 14, 19, 10 | |
| `2026-11-25-volee4` | 19, 2, 6 | |
| `2026-11-25-volee5` | 2, Out | Out du côté opposé aux caméras 1 et 3 ; troisième photo retirée (fausse alerte sans nouvelle fléchette, la troisième fléchette n'a pas été photographiée) |
| `2026-11-25-volee6` | 8, 13, 19 | |
| `2026-11-25-volee7` | 25, 15, 16 | le 16 déplace une fléchette voisine dans la vue de la caméra 1 |
| `2026-11-25-volee8` | 17, T9, 6 | |
| `2026-11-25-volee9` | 11, 6, 7 | |
| `2026-11-25-volee10` | 14, 2, 16 | |
| `2026-11-25-volee11` | T15, 7, 18 | |
| `2026-11-25-volee12` | D14, 3, 13 | photo vide prise avec l'ombre d'une personne sur la cible |
| `2026-11-25-volee13` | 14, 3, 5 | |
| `2026-11-25-volee14` | 14, 3, 18 | |
| `2026-11-25-volee15` | 11, 3, 17 | |
| `2026-11-25-volee16` | 15, 12, 9 | |

## Mesurer la détection

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python tools\detect_photos.py (Get-ChildItem photos -Directory).FullName
```

Pour chaque série : calibration automatique de chaque caméra sur sa photo vide, détection de chaque fléchette, comparaison avec `points.txt`. Le terminal affiche le tableau réel / détecté et le nombre de zones justes. Dans `data/detection/` : grille de calibration des trois caméras, axe repéré par chaque caméra pour chaque fléchette, vue de face avec les positions détectées (vert si juste, rouge sinon), `resultats.md`.

Résultat de référence (prototype des droites projetées, PC de développement) : 47 zones justes sur 56.

- Séries du 19/11 : 5 sur 9. Série 3 entièrement juste, droites des trois caméras concordantes à 1 mm près. Série 1 fausse : fléchettes groupées qui se masquent ou bougent quand on plante la suivante, fûts noirs peu visibles sur les secteurs noirs, fléchette éloignée d'une caméra qui dépasse du masque de la cible.
- Volées du 25/11 : 42 sur 47. Échecs : photo vide qui n'est pas vide (volées 2 et 12), fléchette sur un fil (volée 2), fléchette du côté opposé coupée par le masque (volées 5 et 12), fléchette voisine déplacée (volée 7).

Une amélioration de la détection se juge en relançant la commande sur toutes les séries : le nombre de zones justes doit augmenter sans faire baisser celles déjà justes.

## Ajouter une série

Nouvelles volées enregistrées en direct par `tools/record_volleys.py` dans `data/captures/<jjmmaa-hhmm>-voleeN/` (exemple : `251126-1518-volee3`), au format de ce dossier ; sans zones tapées, la volée est gardée sans `points.txt`. Procédure de séance : [docs/test-detection.md](../docs/test-detection.md).

Les volées utiles sont copiées ici dans `<aaaa-mm-jj>-volee<n>`, après vérification des photos : une photo sans nouvelle fléchette est retirée avec sa zone. Une volée pèse environ 1,7 Mo : en ajouter se décide en équipe.
