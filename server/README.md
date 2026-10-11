# Serveur Wiqaya : modèle code208 + site web

Le serveur sert le site (`website/`) et une API qui fait tourner le modèle de risque
d'incendie de la forêt de Bouhachem / Jbel Sougna.

## Lancer le site

Depuis la racine du dépôt, avec Python 3.11 ou plus récent :

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r server/requirements.txt
python server/app.py
```

Ouvrir ensuite <http://localhost:8000>. La carte plein écran est sur <http://localhost:8000/carte.html>.

Le premier lancement prépare le modèle : grille, facteurs du terrain, FIRMS, validation. Cela prend de 3 à 5 minutes.
Le résultat est gardé dans `server/cache/`, et les lancements suivants démarrent en quelques secondes.
Si un fichier de `data/` change, le modèle est recalculé automatiquement.

## Ce que fait le modèle

Il reprend les parties du notebook `model/code208_risque_feu_autonome.ipynb` que les données du dépôt permettent de faire tourner :

| Étape | Notebook | Ici |
|---|---|---|
| Grille unique de 250 m sur les 6 parties de la forêt | cellule 3 | identique (6 071 cellules) |
| Altitude, pente, exposition (MNT), population | cellule 9 | identique |
| Occupation du sol, distances OSM (routes, douars…) | cellule 9 | **absentes** (fichiers manquants dans `data/`) |
| Années depuis le dernier feu + règle du combustible | cellule 22 | FIRMS seulement (pas les zones brûlées dNBR) |
| Susceptibilité annuelle, validation « une année exclue » | cellule 32 | identique (régression logistique ou RandomForest, le meilleur des deux) |
| Danger météo du jour (Open-Meteo / climatologie d'été 2017-2024) | cellule 27 | identique |
| Carte du jour : 5 classes KMeans + alerte sur 20 % de la forêt | cellule 34 | identique, à partir de la susceptibilité |
| Modèle spatial « jour de feu » (images Sentinel-2 / Landsat) | cellules 11-25 | **non repris** (1 h 30 à 3 h de téléchargement) |

Le modèle utilisé par le site est appris sur toutes les années complètes de FIRMS. Il est appliqué à la date du jour, avec l'historique des feux connu à cette date.
Les scores de validation et des tests indépendants sont renvoyés par l'API dans `resume.modele`.

## API

| Route | Contenu |
|---|---|
| `GET /api/risque[?date=AAAA-MM-JJ]` | cellules en GeoJSON (WGS 84) : `susceptibilite`, `classe_risque` (1 à 5), `alerte_feu`… Le `resume` contient le danger météo et les scores du modèle |
| `GET /api/feux?date=AAAA-MM-JJ[&jours=N]` | détections FIRMS à moins de 5 km de la forêt |
| `GET /api/foret` | limites des 6 parties de la forêt |
| `POST /api/trpc/alerts.subscribe` | formulaire d'alerte du site. Les inscriptions sont enregistrées dans `server/cache/inscriptions.jsonl` (non versionné) |

## Variables d'environnement

- `PORT` : port du serveur, 8000 par défaut.
- `HOST` : adresse d'écoute, `127.0.0.1` par défaut.
- `WIQAYA_DATA` : dossier des données, `data` par défaut.
- `WIQAYA_CACHE` : dossier du cache, `server/cache` par défaut.

Il faut une connexion internet : la météo et la climatologie viennent d'Open-Meteo, et le fond de carte d'OpenStreetMap.
Si Open-Meteo ne répond pas, la carte s'affiche quand même et le danger météo apparaît comme « Non disponible ».
