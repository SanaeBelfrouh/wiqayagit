"""Modèle de risque d'incendie code208 (forêt de Bouhachem / Jbel Sougna), version servie par le site Wiqaya.

Reprend les parties du notebook `model/code208_risque_feu_autonome.ipynb` qui tournent avec les données du dépôt :
  - grille unique de 250 m sur les 6 parties de la forêt (cellule 3) ;
  - facteurs structurels : altitude, pente, exposition (MNT), population (cellule 9) ;
  - historique des feux FIRMS -> années depuis le dernier feu + règle du combustible (cellule 22) ;
  - carte de susceptibilité annuelle apprise sur FIRMS, validation "une année exclue" (cellule 32) ;
  - danger météo du jour Open-Meteo comparé à la climatologie d'été 2017-2024 (cellule 27) ;
  - carte du jour = susceptibilité + 5 classes KMeans + alerte sur le top FRACTION_ALERTE (cellule 34).

Différences avec le notebook, faute de données dans le dépôt :
  - pas d'occupation du sol (combustibilite_01) ni de distances OSM (routes, pistes, douars...) ;
  - historique des feux tiré des seuls points FIRMS (pas des zones brûlées dNBR Sentinel-2/Landsat) ;
  - le modèle spatial "jour de feu" (cellules 21-25), qui exige les images satellite, n'est pas repris :
    la carte du jour utilise la susceptibilité, mise à jour avec l'historique des feux à la date du jour.
"""
import hashlib
import json
import logging
import math
import os
import threading
import time
from pathlib import Path

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterstats import zonal_stats
from shapely.geometry import box
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

log = logging.getLogger('wiqaya.modele')

RACINE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('WIQAYA_DATA', RACINE / 'data'))
FOREST = DATA / 'forest' / 'limites_forets.shp'
DEM = DATA / 'dem' / 'mnt_bouhachem.tif'
POPULATION = DATA / 'population' / 'population_2017_26191_100m.tif'
FIRMS_DIR = DATA / 'firms'
CACHE = Path(os.environ.get('WIQAYA_CACHE', RACINE / 'server' / 'cache'))

# Mêmes constantes que le notebook (cellules 2, 22 et 32).
CRS = 'EPSG:26191'; GRID = 250; SEED = 93
RAYON_HISTORIQUE_M = 375      # demi-taille d'un pixel VIIRS
ANNEES_MAX = 20.0             # "aucun feu connu"
FACTEUR_1_5_ANS = 0.5
ANNEES_APPRENTISSAGE = list(range(2017, 2025))
ANNEE_TEST = 2025
MOIS_ETE = [6, 7, 8, 9]
DANGER_VARS = {'temperature_2m_max': +1, 'vpd_max': +1, 'wind_speed_10m_max': +1, 'relative_humidity_2m_min': -1}
FRACTION_ALERTE = 0.20        # 20 % de la forêt en alerte, comme les cartes S2 du notebook
FUSEAU = 'Africa/Casablanca'
FEATURES = ['altitude_m', 'pente_pct', 'exposition_nord', 'exposition_est', 'population',
            'annees_depuis_dernier_feu', 'brule_moins_5ans']
VERSION_CACHE = 2


def make_model():
    return Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)),
                     ('rf', RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=10, max_features='sqrt',
                                                   class_weight='balanced_subsample', n_jobs=-1, random_state=SEED))])


def make_model_logreg():
    return Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)),
                     ('scale', StandardScaler()),
                     ('logreg', LogisticRegression(C=0.5, class_weight='balanced', max_iter=2000, random_state=SEED))])


CANDIDATS = {'Régression logistique': make_model_logreg, 'RandomForest (régularisé)': make_model}


def regle_combustible(prob, annees):
    """Une zone brûlée il y a moins d'un an n'a plus de combustible ; entre 1 et 5 ans, risque divisé par 2."""
    prob = np.asarray(prob, float).copy(); a = np.asarray(annees, float)
    prob[a < 1] = 0.; prob[(a >= 1) & (a < 5)] *= FACTEUR_1_5_ANS
    return prob


def classes_risque_non_supervisees(probabilities, n_classes=5):
    values = np.asarray(probabilities, dtype=float).reshape(-1, 1)
    k = min(n_classes, len(np.unique(values[np.isfinite(values)])))
    if k < 2:
        return np.ones(len(values), dtype='uint8')
    km = KMeans(n_clusters=k, n_init=30, random_state=SEED).fit(values)
    order = np.argsort(km.cluster_centers_.ravel())
    mapping = {cluster: rank + 1 for rank, cluster in enumerate(order)}
    return np.asarray([mapping[x] for x in km.labels_], dtype='uint8')


def matrice_alerte_relative(prob, verite, fraction):
    prob = np.asarray(prob, float); verite = np.asarray(verite).astype(int)
    alerte = prob >= float(np.quantile(prob, 1 - fraction))
    vp = int((alerte & (verite == 1)).sum()); fn = int((~alerte & (verite == 1)).sum()); fp = int((alerte & (verite == 0)).sum())
    return {'precision': vp / max(vp + fp, 1), 'rappel': vp / max(vp + fn, 1)}


# ----------------------------------------------------------------------------------------------------------------
# Préparation : grille, facteurs structurels, FIRMS (calculés une fois puis mis en cache)
# ----------------------------------------------------------------------------------------------------------------
def _grille(forest):
    foret_unique = forest.geometry.union_all()
    minx, miny, maxx, maxy = foret_unique.bounds
    sindex = forest.sindex
    rows = []
    for x in np.arange(math.floor(minx / GRID) * GRID, maxx, GRID):
        for y in np.arange(math.floor(miny / GRID) * GRID, maxy, GRID):
            carre = box(x, y, x + GRID, y + GRID)
            geom = carre.intersection(foret_unique)
            if geom.is_empty or geom.area < 100:
                continue
            cand = forest.iloc[list(sindex.query(carre, predicate='intersects'))]
            partie = cand.partie.iloc[int(np.argmax(cand.geometry.intersection(carre).area.to_numpy()))] if len(cand) else '?'
            rows.append({'id_cell': f'foret_{len(rows):05d}', 'partie': partie, 'geometry': geom})
    return gpd.GeoDataFrame(rows, crs=CRS)


def _facteurs_structurels(grid):
    structural = grid.copy()
    with rasterio.open(DEM) as src:
        dem = src.read(1).astype('float32')
        dem[(dem == src.nodata) if src.nodata is not None else ~np.isfinite(dem)] = np.nan
        dzdy, dzdx = np.gradient(dem, abs(src.transform.e), abs(src.transform.a))
        slope = np.sqrt(dzdx ** 2 + dzdy ** 2) * 100
        aspect = (np.degrees(np.arctan2(-dzdx, dzdy)) + 360) % 360
        cells = structural.to_crs(src.crs)
        kw = dict(affine=src.transform, stats=['mean'], nodata=np.nan, all_touched=True)
        zs = zonal_stats(cells, dem, **kw); ps = zonal_stats(cells, slope, **kw)
        az_sin = zonal_stats(cells, np.sin(np.radians(aspect)), **kw)
        az_cos = zonal_stats(cells, np.cos(np.radians(aspect)), **kw)
    moyenne = lambda zz: np.array([np.nan if z['mean'] is None else z['mean'] for z in zz], float)
    structural['altitude_m'] = moyenne(zs)
    structural['pente_pct'] = moyenne(ps)
    structural['exposition_deg'] = (np.degrees(np.arctan2(moyenne(az_sin), moyenne(az_cos))) + 360) % 360
    with rasterio.open(POPULATION) as src:
        pop = zonal_stats(structural.to_crs(src.crs), str(POPULATION), stats=['sum'], nodata=src.nodata, all_touched=True)
    structural['population'] = [z['sum'] if z['sum'] is not None else 0. for z in pop]
    structural['exposition_nord'] = np.cos(np.radians(structural['exposition_deg']))
    structural['exposition_est'] = np.sin(np.radians(structural['exposition_deg']))
    return structural


def _firms(forest):
    frames = []
    for path in sorted(FIRMS_DIR.rglob('fire_*.shp')):
        f = gpd.read_file(path)
        if f.crs is None:
            raise ValueError('Fichier FIRMS sans projection (.prj manquant) : ' + str(path))
        f = f.to_crs(CRS)
        f['date'] = pd.to_datetime(f['ACQ_DATE'], errors='coerce').dt.normalize()
        f['frp'] = pd.to_numeric(f['FRP'], errors='coerce').fillna(0)
        frames.append(f[['date', 'frp', 'geometry']])
    firms = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=CRS).dropna(subset=['date'])
    firms = firms[firms.geometry.intersects(forest.geometry.union_all().buffer(5000))]
    return firms.drop_duplicates(subset=['date', 'geometry']).sort_values('date').reset_index(drop=True)


def _signature_donnees():
    """Empreinte du contenu des données (et non de leur date : un changement de branche Git ne relance pas le calcul)."""
    fichiers = [FOREST, DEM, POPULATION] + sorted(FIRMS_DIR.rglob('fire_*.*'))
    def empreinte(p):
        h = hashlib.sha1()
        with p.open('rb') as f:
            for bloc in iter(lambda: f.read(1 << 20), b''):
                h.update(bloc)
        return h.hexdigest()
    return [(str(p.relative_to(DATA)), empreinte(p)) for p in fichiers]


class ModeleRisque:
    """Charge (ou calcule puis met en cache) tout ce qui ne dépend pas du jour, puis produit la carte du jour."""

    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        cache = CACHE / 'modele_code208_web.joblib'
        signature = {'version': VERSION_CACHE, 'donnees': _signature_donnees()}
        etat = joblib.load(cache) if cache.exists() else None
        if etat is None or etat.get('signature') != signature:
            log.info('Préparation du modèle (grille, facteurs, FIRMS, validation) : ~1 à 3 min la première fois...')
            t0 = time.time()
            etat = self._preparer(); etat['signature'] = signature
            joblib.dump(etat, cache)
            log.info('Modèle prêt en %.0f s, mis en cache dans %s', time.time() - t0, cache)
        self.__dict__.update(etat)
        self.foret_unique = self.forest.geometry.union_all()
        self._verrou = threading.Lock()
        self._cartes = {}
        self._meteo = {}
        self._climato = None; self._climato_essai = 0.

    # -- préparation (une fois) ----------------------------------------------------------------------------------
    def _preparer(self):
        forest = gpd.read_file(FOREST)
        forest = forest.set_crs(CRS, allow_override=True) if forest.crs is None else forest.to_crs(CRS)
        forest['partie'] = forest['nom'].astype(str).str.lower() if 'nom' in forest else [chr(97 + k) for k in range(len(forest))]
        grid = _grille(forest)
        structural = _facteurs_structurels(grid)
        firms = _firms(forest)
        pts = firms[['date', 'geometry']].copy(); pts['geometry'] = pts.geometry.buffer(RAYON_HISTORIQUE_M)
        historique = gpd.sjoin(pts, grid[['id_cell', 'geometry']], predicate='intersects', how='inner')[['id_cell', 'date']]
        historique = pd.DataFrame(historique).reset_index(drop=True)
        etat = {'forest': forest, 'structural': structural, 'firms': firms, 'historique': historique}
        etat.update(self._apprendre(structural, firms, historique, forest.geometry.union_all()))
        return etat

    @staticmethod
    def _ajouter_historique(frame, historique, date):
        date = pd.Timestamp(date).normalize()
        dernier = historique[historique.date < date].groupby('id_cell').date.max()
        annees = ((date - dernier).dt.days / 365.25).clip(0, ANNEES_MAX)
        frame = frame.copy()
        frame['annees_depuis_dernier_feu'] = frame.id_cell.map(annees).fillna(ANNEES_MAX).to_numpy()
        frame['brule_moins_5ans'] = (frame['annees_depuis_dernier_feu'] < 5).astype(int)
        return frame

    @staticmethod
    def _cellules_avec_firms(base, firms, foret_unique, debut, fin):
        pts = firms[(firms.date >= pd.Timestamp(debut)) & (firms.date <= pd.Timestamp(fin))]
        pts = pts[pts.geometry.within(foret_unique)]
        j = gpd.sjoin(pts[['geometry']], base[['id_cell', 'geometry']], predicate='within', how='inner')
        return base.id_cell.isin(j.id_cell).astype(int).to_numpy(), len(pts)

    def _apprendre(self, base, firms, historique, foret_unique):
        def panneau(annees):
            morceaux = []
            for an in annees:
                f = self._ajouter_historique(base, historique, f'{an}-01-01')
                f['feu_firms'], _ = self._cellules_avec_firms(base, firms, foret_unique, f'{an}-01-01', f'{an}-12-31')
                f['annee'] = an; morceaux.append(f)
            return pd.concat(morceaux, ignore_index=True)

        # 1) Validation "une année exclue" sur 2017-2024 et choix du modèle (cellule 32 du notebook).
        p = panneau(ANNEES_APPRENTISSAGE)
        X, y, groupes = p[FEATURES], p.feu_firms, p.annee
        lignes = []
        for nom, fab in CANDIDATS.items():
            pred = np.zeros(len(p)); par_an = {}
            for tr, te in LeaveOneGroupOut().split(X, y, groupes):
                m = fab(); m.fit(X.iloc[tr], y.iloc[tr])
                pred[te] = regle_combustible(m.predict_proba(X.iloc[te])[:, 1], X.iloc[te]['annees_depuis_dernier_feu'])
                yt = y.iloc[te]
                if 0 < yt.sum() < len(yt):
                    par_an[int(groupes.iloc[te[0]])] = roc_auc_score(yt, pred[te])
            lignes.append({'modele': nom, 'roc_auc_global': roc_auc_score(y, pred),
                           'pr_lift': average_precision_score(y, pred) / y.mean(),
                           'roc_auc_moyen_par_annee': float(np.mean(list(par_an.values()))),
                           'roc_auc_par_annee': {str(a): v for a, v in par_an.items()}})
        validation = sorted(lignes, key=lambda r: -r['roc_auc_moyen_par_annee'])
        nom_modele = validation[0]['modele']

        def tester(modele, annee_hist, debut, fin, libelle):
            t = self._ajouter_historique(base, historique, annee_hist)
            vrai, n = self._cellules_avec_firms(base, firms, foret_unique, debut, fin)
            prob = regle_combustible(modele.predict_proba(t[FEATURES])[:, 1], t['annees_depuis_dernier_feu'])
            if not 0 < vrai.sum() < len(vrai):
                return {'test': libelle, 'points_firms': n, 'cellules_feu': int(vrai.sum()), 'roc_auc': None}
            m = matrice_alerte_relative(prob, vrai, FRACTION_ALERTE)
            return {'test': libelle, 'points_firms': n, 'cellules_feu': int(vrai.sum()), 'roc_auc': roc_auc_score(vrai, prob),
                    'pr_lift': average_precision_score(vrai, prob) / vrai.mean(), 'rappel_top20': m['rappel'],
                    'precision_top20': m['precision'], 'precision_hasard': float(vrai.mean())}

        # 2) Test indépendant 2025, modèle appris sur 2017-2024 (historique au 1er août 2025, comme le notebook).
        m_2024 = CANDIDATS[nom_modele](); m_2024.fit(X, y)
        tests = [tester(m_2024, f'{ANNEE_TEST}-08-01', f'{ANNEE_TEST}-01-01', f'{ANNEE_TEST}-12-31',
                        f'FIRMS {ANNEE_TEST} (appris sur 2017-2024)')]

        # 3) Modèle opérationnel : appris sur toutes les années complètes disponibles avant l'année en cours.
        derniere = int(firms.date.max().year)
        annees_op = list(range(ANNEES_APPRENTISSAGE[0], derniere))
        p_op = p if annees_op == ANNEES_APPRENTISSAGE else panneau(annees_op)
        modele = CANDIDATS[nom_modele](); modele.fit(p_op[FEATURES], p_op.feu_firms)
        if annees_op[-1] >= ANNEE_TEST:   # l'année en cours n'a jamais été vue par le modèle opérationnel
            tests.append(tester(modele, f'{derniere}-01-01', f'{derniere}-01-01', f'{derniere}-12-31',
                                f'FIRMS {derniere} jusqu\'au {firms.date.max().date()} (appris sur {annees_op[0]}-{annees_op[-1]})'))
        est = modele.steps[-1][1]
        importance = np.abs(est.coef_[0]) if hasattr(est, 'coef_') else est.feature_importances_
        return {'modele': modele, 'nom_modele': nom_modele, 'annees_modele': [annees_op[0], annees_op[-1]],
                'validation': validation, 'tests': tests,
                'importance': dict(sorted(zip(FEATURES, map(float, importance)), key=lambda kv: -kv[1]))}

    # -- météo ---------------------------------------------------------------------------------------------------
    @property
    def centre_wgs84(self):
        c = gpd.GeoSeries([self.foret_unique.centroid], crs=CRS).to_crs('EPSG:4326').iloc[0]
        return float(c.y), float(c.x)

    @staticmethod
    def _journalier(h):
        df = pd.DataFrame({'time': pd.to_datetime(h['time']), 't': h['temperature_2m'], 'hr': h['relative_humidity_2m'],
                           'v': h['wind_speed_10m']}).astype({'t': float, 'hr': float, 'v': float})
        df['vpd'] = .6108 * np.exp(17.27 * df.t / (df.t + 237.3)) * (1 - df.hr / 100)
        df['date'] = df.time.dt.normalize()
        return df.groupby('date').agg(temperature_2m_max=('t', 'max'), relative_humidity_2m_min=('hr', 'min'),
                                      wind_speed_10m_max=('v', 'max'), vpd_max=('vpd', 'max')).reset_index()

    def climatologie(self):
        """Climatologie d'été 2017-2024 (juin-septembre) au centre de la forêt, téléchargée une fois puis en cache."""
        if self._climato is not None:
            return self._climato
        fichier = CACHE / 'climatologie_ete_2017_2024.csv'
        if fichier.exists():
            self._climato = pd.read_csv(fichier, parse_dates=['date']); return self._climato
        if time.time() - self._climato_essai < 600:   # pas plus d'un essai toutes les 10 min si Open-Meteo refuse
            return None
        self._climato_essai = time.time()
        lat, lon = self.centre_wgs84
        try:
            r = requests.get('https://archive-api.open-meteo.com/v1/archive', timeout=180, params={
                'latitude': lat, 'longitude': lon, 'start_date': '2017-06-01', 'end_date': '2024-09-30',
                'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m', 'timezone': FUSEAU})
            r.raise_for_status()
        except requests.RequestException as e:
            log.warning('Climatologie Open-Meteo indisponible : %s', e); return None
        c = self._journalier(r.json()['hourly'])
        c = c[c.date.dt.month.isin(MOIS_ETE)].reset_index(drop=True)
        c.to_csv(fichier, index=False)
        self._climato = c
        return c

    def meteo_du_jour(self, date):
        """Météo prévue (Open-Meteo) au centre de la forêt pour `date`, mise en cache 1 h."""
        cle = str(date.date())
        if cle in self._meteo and time.time() - self._meteo[cle][0] < 3600:
            return self._meteo[cle][1]
        lat, lon = self.centre_wgs84
        try:
            r = requests.get('https://api.open-meteo.com/v1/forecast', timeout=30, params={
                'latitude': lat, 'longitude': lon, 'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m',
                'start_date': cle, 'end_date': cle, 'timezone': FUSEAU})
            r.raise_for_status()
            j = self._journalier(r.json()['hourly'])
            meteo = {k: float(j[k].iloc[0]) for k in DANGER_VARS} if len(j) else None
        except (requests.RequestException, KeyError, ValueError) as e:
            log.warning('Météo Open-Meteo indisponible : %s', e); meteo = None
        self._meteo[cle] = (time.time(), meteo)
        return meteo

    def danger_du_jour(self, date):
        meteo = self.meteo_du_jour(date)
        climato = self.climatologie()
        if meteo is None or climato is None:
            manque = 'la météo du jour' if meteo is None else 'la climatologie d\'été 2017-2024'
            return {'indice': None, 'classe': 'inconnu', 'parts': {}, 'meteo': meteo,
                    'message': f'Open-Meteo n\'a pas fourni {manque} : danger météo non calculé.'}
        return {**indice_danger(meteo, climato), 'meteo': meteo}

    # -- carte du jour -------------------------------------------------------------------------------------------
    def carte_du_jour(self, date=None):
        date = pd.Timestamp(date) if date is not None else pd.Timestamp.now(tz=FUSEAU).tz_localize(None)
        date = date.normalize()
        with self._verrou:
            cle = str(date.date())
            if cle not in self._cartes:
                t = self._ajouter_historique(self.structural, self.historique, date)
                t['susceptibilite'] = regle_combustible(self.modele.predict_proba(t[FEATURES])[:, 1], t['annees_depuis_dernier_feu'])
                t['classe_risque'] = classes_risque_non_supervisees(t.susceptibilite, 5)
                seuil = float(np.quantile(t.susceptibilite, 1 - FRACTION_ALERTE))
                t['alerte_feu'] = (t.susceptibilite >= seuil).astype('uint8')
                self._cartes = {cle: (t, seuil)}   # une seule date gardée en mémoire
            t, seuil = self._cartes[cle]
        danger = self.danger_du_jour(date)
        return t, {'date': str(date.date()), 'seuil_alerte': seuil, 'fraction_alerte': FRACTION_ALERTE, 'danger': danger,
                   'alerte_operationnelle': danger['classe'] in ('élevé', 'très élevé'),
                   'modele': {'nom': self.nom_modele, 'annees_apprentissage': self.annees_modele, 'variables': FEATURES,
                              'importance': self.importance, 'validation_une_annee_exclue': self.validation,
                              'tests_independants': self.tests},
                   'firms_jusqu_au': str(self.firms.date.max().date())}

    def feux(self, debut, fin):
        f = self.firms[(self.firms.date >= pd.Timestamp(debut)) & (self.firms.date <= pd.Timestamp(fin))].copy()
        f['dans_foret'] = f.geometry.within(self.foret_unique)
        f['date'] = f.date.dt.strftime('%Y-%m-%d')
        return f


def indice_danger(meteo, climato):
    """Indice de danger météo (0-1) : part des journées d'été 2017-2024 moins dangereuses que le jour étudié."""
    parts = {}
    for var, sens in DANGER_VARS.items():
        if meteo.get(var) is None or var not in climato:
            continue
        ref = climato[var].dropna()
        if ref.empty:
            continue
        parts[var] = float((ref <= meteo[var]).mean()) if sens > 0 else float((ref >= meteo[var]).mean())
    if not parts:
        return {'indice': None, 'classe': 'inconnu', 'parts': parts}
    indice = float(np.mean(list(parts.values())))
    classe = 'faible' if indice < 0.25 else 'modéré' if indice < 0.50 else 'élevé' if indice < 0.75 else 'très élevé'
    return {'indice': indice, 'classe': classe, 'parts': parts}


def vers_geojson(gdf, colonnes, decimales=5, simplification_m=0):
    """GeoDataFrame -> dict GeoJSON en WGS 84 (géométries simplifiées et coordonnées arrondies pour l'affichage web)."""
    g = gdf[colonnes + ['geometry']].copy()
    if simplification_m:
        g['geometry'] = g.geometry.simplify(simplification_m, preserve_topology=True)
    g = g.to_crs('EPSG:4326')
    g['geometry'] = g.geometry.set_precision(10 ** -decimales)
    return json.loads(g.to_json(na='null', drop_id=True))
