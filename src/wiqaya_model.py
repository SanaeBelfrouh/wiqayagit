"""Wiqaya fire-risk model for the Bouhachem / Derdara / Jbel Sougna forests (northern Morocco).

Reproducible core of the research notebook `research/code208_risque_feu_autonome.ipynb`, restricted to the
inputs shipped in `data/sample_input/`:

  1. one 250 m grid over the 6 forest parts (EPSG:26191, Merchich / Nord Maroc);
  2. terrain (elevation, slope, aspect from the DEM) and population (WorldPop 2017) per cell;
  3. fire history from NASA FIRMS -> years since the last fire, and the fuel rule;
  4. yearly susceptibility model learned from FIRMS, validated leave-one-year-out (2017-2024),
     blind-tested on 2025;
  5. daily weather danger index (Open-Meteo forecast ranked against the 2017-2024 summers);
  6. daily map: 5 KMeans risk classes and an alert on the riskiest FRACTION_ALERT of the forest.

Used by `server/app.py` (web platform).
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

log = logging.getLogger('wiqaya.model')

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('WIQAYA_DATA', ROOT / 'data' / 'sample_input'))
FOREST = DATA / 'forest_boundaries.gpkg'
DEM = DATA / 'dem_30m.tif'
POPULATION = DATA / 'population_2017_100m.tif'
FIRMS = DATA / 'firms_fire_detections.gpkg'
CACHE = Path(os.environ.get('WIQAYA_CACHE', ROOT / 'server' / 'cache'))

# Same parameters as the research notebook.
CRS = 'EPSG:26191'
GRID = 250                      # cell size (m)
SEED = 93
HISTORY_RADIUS_M = 375          # half a VIIRS pixel: a FIRMS point marks the cells within this distance as burned
YEARS_MAX = 20.0                # "no known fire"
FACTOR_1_5_YEARS = 0.5          # fuel rule: risk halved 1 to 5 years after a fire
TRAINING_YEARS = list(range(2017, 2025))
TEST_YEAR = 2025
SUMMER_MONTHS = [6, 7, 8, 9]
DANGER_VARS = {'temperature_2m_max': +1, 'vpd_max': +1, 'wind_speed_10m_max': +1, 'relative_humidity_2m_min': -1}
FRACTION_ALERT = 0.20           # share of the forest in alert
TIMEZONE = 'Africa/Casablanca'
FEATURES = ['elevation_m', 'slope_pct', 'aspect_north', 'aspect_east', 'population',
            'years_since_last_fire', 'burned_last_5y']
CACHE_VERSION = 3


# ------------------------------------------------------------------------------------------------------------
# Models and rules
# ------------------------------------------------------------------------------------------------------------
def make_random_forest():
    return Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)),
                     ('rf', RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=10, max_features='sqrt',
                                                   class_weight='balanced_subsample', n_jobs=-1, random_state=SEED))])


def make_logistic_regression():
    return Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)),
                     ('scale', StandardScaler()),
                     ('logreg', LogisticRegression(C=0.5, class_weight='balanced', max_iter=2000, random_state=SEED))])


CANDIDATE_MODELS = {'Logistic regression': make_logistic_regression, 'Random forest (regularised)': make_random_forest}


def fuel_rule(prob, years_since_fire):
    """No fuel left less than a year after a fire; risk halved between 1 and 5 years after it."""
    prob = np.asarray(prob, float).copy()
    years = np.asarray(years_since_fire, float)
    prob[years < 1] = 0.
    prob[(years >= 1) & (years < 5)] *= FACTOR_1_5_YEARS
    return prob


def risk_classes(prob, n_classes=5):
    """Unsupervised risk classes 1 (lowest) to n (highest): KMeans on the probabilities."""
    values = np.asarray(prob, dtype=float).reshape(-1, 1)
    k = min(n_classes, len(np.unique(values[np.isfinite(values)])))
    if k < 2:
        return np.ones(len(values), dtype='uint8')
    km = KMeans(n_clusters=k, n_init=30, random_state=SEED).fit(values)
    order = np.argsort(km.cluster_centers_.ravel())
    rank = {cluster: r + 1 for r, cluster in enumerate(order)}
    return np.asarray([rank[c] for c in km.labels_], dtype='uint8')


def alert_metrics(prob, truth, fraction):
    """Precision and recall when the riskiest `fraction` of the cells is put in alert."""
    prob = np.asarray(prob, float)
    truth = np.asarray(truth).astype(int)
    alert = prob >= float(np.quantile(prob, 1 - fraction))
    tp = int((alert & (truth == 1)).sum())
    fn = int((~alert & (truth == 1)).sum())
    fp = int((alert & (truth == 0)).sum())
    return {'precision': tp / max(tp + fp, 1), 'recall': tp / max(tp + fn, 1)}


# ------------------------------------------------------------------------------------------------------------
# Inputs, grid and features
# ------------------------------------------------------------------------------------------------------------
def load_forest():
    forest = gpd.read_file(FOREST)
    return forest.set_crs(CRS, allow_override=True) if forest.crs is None else forest.to_crs(CRS)


def build_grid(forest):
    """One 250 m grid over the union of the forest parts; each cell is clipped to the forest."""
    union = forest.geometry.union_all()
    minx, miny, maxx, maxy = union.bounds
    index = forest.sindex
    rows = []
    for x in np.arange(math.floor(minx / GRID) * GRID, maxx, GRID):
        for y in np.arange(math.floor(miny / GRID) * GRID, maxy, GRID):
            square = box(x, y, x + GRID, y + GRID)
            geom = square.intersection(union)
            if geom.is_empty or geom.area < 100:
                continue
            parts = forest.iloc[list(index.query(square, predicate='intersects'))]
            part = parts.part.iloc[int(np.argmax(parts.geometry.intersection(square).area.to_numpy()))] if len(parts) else '?'
            rows.append({'cell_id': f'cell_{len(rows):05d}', 'part': part, 'geometry': geom})
    return gpd.GeoDataFrame(rows, crs=CRS)


def terrain_and_population(grid):
    """Mean elevation, slope and aspect (circular mean) from the DEM, and population from WorldPop."""
    cells = grid.copy()
    with rasterio.open(DEM) as src:
        dem = src.read(1).astype('float32')
        dem[(dem == src.nodata) if src.nodata is not None else ~np.isfinite(dem)] = np.nan
        dzdy, dzdx = np.gradient(dem, abs(src.transform.e), abs(src.transform.a))
        slope = np.sqrt(dzdx ** 2 + dzdy ** 2) * 100
        aspect = (np.degrees(np.arctan2(-dzdx, dzdy)) + 360) % 360
        geoms = cells.to_crs(src.crs)
        kw = dict(affine=src.transform, stats=['mean'], nodata=np.nan, all_touched=True)
        mean = lambda stats: np.array([np.nan if s['mean'] is None else s['mean'] for s in stats], float)
        cells['elevation_m'] = mean(zonal_stats(geoms, dem, **kw))
        cells['slope_pct'] = mean(zonal_stats(geoms, slope, **kw))
        # Circular mean: a plain mean of 355 deg and 5 deg would give 180 deg (south) instead of north.
        sin_ = mean(zonal_stats(geoms, np.sin(np.radians(aspect)), **kw))
        cos_ = mean(zonal_stats(geoms, np.cos(np.radians(aspect)), **kw))
    cells['aspect_deg'] = (np.degrees(np.arctan2(sin_, cos_)) + 360) % 360
    cells['aspect_north'] = np.cos(np.radians(cells['aspect_deg']))
    cells['aspect_east'] = np.sin(np.radians(cells['aspect_deg']))
    with rasterio.open(POPULATION) as src:
        pop = zonal_stats(cells.to_crs(src.crs), str(POPULATION), stats=['sum'], nodata=src.nodata, all_touched=True)
    cells['population'] = [s['sum'] if s['sum'] is not None else 0. for s in pop]
    return cells


def load_firms(forest):
    """NASA FIRMS detections (MODIS + VIIRS) within 5 km of the forest, one row per date and location."""
    f = gpd.read_file(FIRMS).to_crs(CRS)
    f['date'] = pd.to_datetime(f['ACQ_DATE'], errors='coerce').dt.normalize()
    f['frp'] = pd.to_numeric(f['FRP'], errors='coerce').fillna(0)
    f = f[['date', 'frp', 'INSTRUMENT', 'geometry']].dropna(subset=['date'])
    f = f[f.geometry.intersects(forest.geometry.union_all().buffer(5000))]
    return f.drop_duplicates(subset=['date', 'geometry']).sort_values('date').reset_index(drop=True)


def fire_history(firms, grid):
    """(cell_id, date) pairs: every cell within HISTORY_RADIUS_M of a FIRMS detection burned that day."""
    pts = firms[['date', 'geometry']].copy()
    pts['geometry'] = pts.geometry.buffer(HISTORY_RADIUS_M)
    joined = gpd.sjoin(pts, grid[['cell_id', 'geometry']], predicate='intersects', how='inner')
    return pd.DataFrame(joined[['cell_id', 'date']]).reset_index(drop=True)


def add_fire_history(frame, history, date):
    """Years since the last fire, using only fires strictly BEFORE `date` (no leakage)."""
    date = pd.Timestamp(date).normalize()
    last = history[history.date < date].groupby('cell_id').date.max()
    years = ((date - last).dt.days / 365.25).clip(0, YEARS_MAX)
    frame = frame.copy()
    frame['years_since_last_fire'] = frame.cell_id.map(years).fillna(YEARS_MAX).to_numpy()
    frame['burned_last_5y'] = (frame['years_since_last_fire'] < 5).astype(int)
    return frame


def cells_with_firms(cells, firms, forest_union, start, end):
    """1 for the cells containing at least one FIRMS detection between `start` and `end` (inside the forest)."""
    pts = firms[(firms.date >= pd.Timestamp(start)) & (firms.date <= pd.Timestamp(end))]
    pts = pts[pts.geometry.within(forest_union)]
    joined = gpd.sjoin(pts[['geometry']], cells[['cell_id', 'geometry']], predicate='within', how='inner')
    return cells.cell_id.isin(joined.cell_id).astype(int).to_numpy(), len(pts)


# ------------------------------------------------------------------------------------------------------------
# Learning and evaluation
# ------------------------------------------------------------------------------------------------------------
def yearly_panel(cells, firms, history, forest_union, years):
    """One row per (cell, year): features with the fire history on 1 January, label = FIRMS fire that year."""
    frames = []
    for year in years:
        f = add_fire_history(cells, history, f'{year}-01-01')
        f['fire'], _ = cells_with_firms(cells, firms, forest_union, f'{year}-01-01', f'{year}-12-31')
        f['year'] = year
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def leave_one_year_out(panel):
    """Validation where each year is held out in turn, for every candidate model. Best model first."""
    X, y, groups = panel[FEATURES], panel.fire, panel.year
    rows = []
    for name, factory in CANDIDATE_MODELS.items():
        pred = np.zeros(len(panel))
        per_year = {}
        for tr, te in LeaveOneGroupOut().split(X, y, groups):
            m = factory()
            m.fit(X.iloc[tr], y.iloc[tr])
            pred[te] = fuel_rule(m.predict_proba(X.iloc[te])[:, 1], X.iloc[te]['years_since_last_fire'])
            yt = y.iloc[te]
            if 0 < yt.sum() < len(yt):
                per_year[int(groups.iloc[te[0]])] = roc_auc_score(yt, pred[te])
        rows.append({'model': name, 'roc_auc_global': roc_auc_score(y, pred),
                     'pr_lift': average_precision_score(y, pred) / y.mean(),
                     'roc_auc_mean_per_year': float(np.mean(list(per_year.values()))),
                     'roc_auc_per_year': {str(a): v for a, v in per_year.items()}})
    return sorted(rows, key=lambda r: -r['roc_auc_mean_per_year'])


def blind_test(model, cells, firms, history, forest_union, history_date, start, end, label):
    """Scores of `model` on the FIRMS fires between `start` and `end`, with the fire history known at `history_date`."""
    t = add_fire_history(cells, history, history_date)
    truth, n = cells_with_firms(cells, firms, forest_union, start, end)
    prob = fuel_rule(model.predict_proba(t[FEATURES])[:, 1], t['years_since_last_fire'])
    if not 0 < truth.sum() < len(truth):
        return {'test': label, 'firms_points': n, 'fire_cells': int(truth.sum()), 'roc_auc': None}
    m = alert_metrics(prob, truth, FRACTION_ALERT)
    return {'test': label, 'firms_points': n, 'fire_cells': int(truth.sum()), 'roc_auc': roc_auc_score(truth, prob),
            'pr_lift': average_precision_score(truth, prob) / truth.mean(), 'recall_top20': m['recall'],
            'precision_top20': m['precision'], 'precision_random': float(truth.mean())}


def feature_importance(model):
    est = model.steps[-1][1]
    values = np.abs(est.coef_[0]) if hasattr(est, 'coef_') else est.feature_importances_
    return dict(sorted(zip(FEATURES, map(float, values)), key=lambda kv: -kv[1]))


def train_and_evaluate(cells, firms, history, forest_union):
    """Model selection (leave-one-year-out 2017-2024), blind test 2025, then the operational model."""
    panel = yearly_panel(cells, firms, history, forest_union, TRAINING_YEARS)
    validation = leave_one_year_out(panel)
    best = validation[0]['model']

    model_2024 = CANDIDATE_MODELS[best]()
    model_2024.fit(panel[FEATURES], panel.fire)
    tests = [blind_test(model_2024, cells, firms, history, forest_union, f'{TEST_YEAR}-08-01',
                        f'{TEST_YEAR}-01-01', f'{TEST_YEAR}-12-31', f'FIRMS {TEST_YEAR} (trained on 2017-2024)')]

    # Operational model: every complete year of FIRMS data before the current year.
    last_year = int(firms.date.max().year)
    years_op = list(range(TRAINING_YEARS[0], last_year))
    panel_op = panel if years_op == TRAINING_YEARS else yearly_panel(cells, firms, history, forest_union, years_op)
    model = CANDIDATE_MODELS[best]()
    model.fit(panel_op[FEATURES], panel_op.fire)
    if years_op[-1] >= TEST_YEAR:   # the current year was never seen by the operational model
        tests.append(blind_test(model, cells, firms, history, forest_union, f'{last_year}-01-01', f'{last_year}-01-01',
                                f'{last_year}-12-31', f'FIRMS {last_year} up to {firms.date.max().date()} '
                                                      f'(trained on {years_op[0]}-{years_op[-1]})'))
    return {'model': model, 'model_2024': model_2024, 'model_name': best, 'model_years': [years_op[0], years_op[-1]],
            'validation': validation, 'tests': tests, 'importance': feature_importance(model)}


def prepare():
    """Every step that does not depend on the day: grid, features, FIRMS, fire history, models."""
    forest = load_forest()
    grid = build_grid(forest)
    cells = terrain_and_population(grid)
    firms = load_firms(forest)
    history = fire_history(firms, grid)
    state = {'forest': forest, 'cells': cells, 'firms': firms, 'history': history}
    state.update(train_and_evaluate(cells, firms, history, forest.geometry.union_all()))
    return state


def susceptibility_map(model, cells, history, date):
    """Susceptibility of every cell on `date`, its 5 risk classes and the alert on the riskiest FRACTION_ALERT."""
    t = add_fire_history(cells, history, date)
    t['susceptibility'] = fuel_rule(model.predict_proba(t[FEATURES])[:, 1], t['years_since_last_fire'])
    t['risk_class'] = risk_classes(t.susceptibility, 5)
    threshold = float(np.quantile(t.susceptibility, 1 - FRACTION_ALERT))
    t['alert'] = (t.susceptibility >= threshold).astype('uint8')
    return t, threshold


# ------------------------------------------------------------------------------------------------------------
# Weather danger of the day (Open-Meteo)
# ------------------------------------------------------------------------------------------------------------
def forest_centre_wgs84(forest):
    c = gpd.GeoSeries([forest.geometry.union_all().centroid], crs=CRS).to_crs('EPSG:4326').iloc[0]
    return float(c.y), float(c.x)


def daily_weather(hourly):
    """Hourly Open-Meteo values -> daily max temperature, min humidity, max wind and max VPD (kPa)."""
    df = pd.DataFrame({'time': pd.to_datetime(hourly['time']), 't': hourly['temperature_2m'],
                       'rh': hourly['relative_humidity_2m'], 'w': hourly['wind_speed_10m']}).astype({'t': float, 'rh': float, 'w': float})
    df['vpd'] = .6108 * np.exp(17.27 * df.t / (df.t + 237.3)) * (1 - df.rh / 100)
    df['date'] = df.time.dt.normalize()
    return df.groupby('date').agg(temperature_2m_max=('t', 'max'), relative_humidity_2m_min=('rh', 'min'),
                                  wind_speed_10m_max=('w', 'max'), vpd_max=('vpd', 'max')).reset_index()


def download_summer_climatology(lat, lon):
    """Every June-September day of 2017-2024 at the forest centre (Open-Meteo ERA5-based archive)."""
    r = requests.get('https://archive-api.open-meteo.com/v1/archive', timeout=180, params={
        'latitude': lat, 'longitude': lon, 'start_date': '2017-06-01', 'end_date': '2024-09-30',
        'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m', 'timezone': TIMEZONE})
    r.raise_for_status()
    c = daily_weather(r.json()['hourly'])
    return c[c.date.dt.month.isin(SUMMER_MONTHS)].reset_index(drop=True)


def download_weather(lat, lon, date):
    """Weather of `date` at the forest centre: forecast (or recent past) from Open-Meteo."""
    day = str(pd.Timestamp(date).date())
    r = requests.get('https://api.open-meteo.com/v1/forecast', timeout=30, params={
        'latitude': lat, 'longitude': lon, 'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m',
        'start_date': day, 'end_date': day, 'timezone': TIMEZONE})
    r.raise_for_status()
    d = daily_weather(r.json()['hourly'])
    return {k: float(d[k].iloc[0]) for k in DANGER_VARS} if len(d) else None


def danger_index(weather, climatology):
    """Weather danger (0-1): share of the 2017-2024 summer days that were less dangerous, averaged over 4 variables."""
    parts = {}
    for var, sign in DANGER_VARS.items():
        if weather.get(var) is None or var not in climatology:
            continue
        ref = climatology[var].dropna()
        if ref.empty:
            continue
        parts[var] = float((ref <= weather[var]).mean()) if sign > 0 else float((ref >= weather[var]).mean())
    if not parts:
        return {'index': None, 'class': 'unknown', 'parts': parts}
    index = float(np.mean(list(parts.values())))
    level = 'low' if index < 0.25 else 'moderate' if index < 0.50 else 'high' if index < 0.75 else 'very high'
    return {'index': index, 'class': level, 'parts': parts}


# ------------------------------------------------------------------------------------------------------------
# Service used by the web platform (caching, today's map, weather)
# ------------------------------------------------------------------------------------------------------------
def _data_fingerprint():
    """Hash of the input files' content: the cache is rebuilt when an input changes, not when its date does."""
    def sha1(p):
        h = hashlib.sha1()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                h.update(block)
        return h.hexdigest()
    return [(p.name, sha1(p)) for p in (FOREST, DEM, POPULATION, FIRMS)]


class RiskService:
    """Loads (or computes and caches) everything that does not depend on the day, then serves the daily map."""

    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        cache = CACHE / 'wiqaya_model.joblib'
        signature = {'version': CACHE_VERSION, 'data': _data_fingerprint()}
        state = joblib.load(cache) if cache.exists() else None
        if state is None or state.get('signature') != signature:
            log.info('Preparing the model (grid, features, FIRMS, validation): 3 to 5 min the first time...')
            t0 = time.time()
            state = prepare()
            state['signature'] = signature
            joblib.dump(state, cache)
            log.info('Model ready in %.0f s, cached in %s', time.time() - t0, cache)
        self.__dict__.update(state)
        self.forest_union = self.forest.geometry.union_all()
        self.centre = forest_centre_wgs84(self.forest)
        self._lock = threading.Lock()
        self._maps = {}
        self._weather = {}
        self._climatology = None
        self._climatology_attempt = 0.

    def climatology(self):
        if self._climatology is not None:
            return self._climatology
        path = CACHE / 'summer_climatology_2017_2024.csv'
        if path.exists():
            self._climatology = pd.read_csv(path, parse_dates=['date'])
            return self._climatology
        if time.time() - self._climatology_attempt < 600:   # at most one attempt every 10 min if Open-Meteo refuses
            return None
        self._climatology_attempt = time.time()
        try:
            c = download_summer_climatology(*self.centre)
        except requests.RequestException as e:
            log.warning('Open-Meteo climatology unavailable: %s', e)
            return None
        c.to_csv(path, index=False)
        self._climatology = c
        return c

    def weather(self, date):
        """Weather of `date`, cached for one hour."""
        key = str(date.date())
        if key in self._weather and time.time() - self._weather[key][0] < 3600:
            return self._weather[key][1]
        try:
            w = download_weather(*self.centre, date)
        except (requests.RequestException, KeyError, ValueError) as e:
            log.warning('Open-Meteo weather unavailable: %s', e)
            w = None
        self._weather[key] = (time.time(), w)
        return w

    def danger(self, date):
        weather, climatology = self.weather(date), self.climatology()
        if weather is None or climatology is None:
            return {'index': None, 'class': 'unknown', 'parts': {}, 'weather': weather}
        return {**danger_index(weather, climatology), 'weather': weather}

    def risk_map(self, date=None):
        date = pd.Timestamp(date) if date is not None else pd.Timestamp.now(tz=TIMEZONE).tz_localize(None)
        date = date.normalize()
        with self._lock:
            key = str(date.date())
            if key not in self._maps:
                self._maps = {key: susceptibility_map(self.model, self.cells, self.history, date)}   # one date in memory
            cells, threshold = self._maps[key]
        danger = self.danger(date)
        return cells, {'date': str(date.date()), 'alert_threshold': threshold, 'alert_fraction': FRACTION_ALERT,
                       'danger': danger, 'operational_alert': danger['class'] in ('high', 'very high'),
                       'model': {'name': self.model_name, 'training_years': self.model_years, 'features': FEATURES,
                                 'importance': self.importance, 'validation_leave_one_year_out': self.validation,
                                 'blind_tests': self.tests},
                       'firms_until': str(self.firms.date.max().date())}

    def fires(self, start, end):
        f = self.firms[(self.firms.date >= pd.Timestamp(start)) & (self.firms.date <= pd.Timestamp(end))].copy()
        f['inside_forest'] = f.geometry.within(self.forest_union)
        f['date'] = f.date.dt.strftime('%Y-%m-%d')
        return f


def to_geojson(gdf, columns, decimals=5, simplify_m=0):
    """GeoDataFrame -> GeoJSON dict in WGS 84, simplified and rounded for the web."""
    g = gdf[columns + ['geometry']].copy()
    if simplify_m:
        g['geometry'] = g.geometry.simplify(simplify_m, preserve_topology=True)
    g = g.to_crs('EPSG:4326')
    g['geometry'] = g.geometry.set_precision(10 ** -decimals)
    return json.loads(g.to_json(na='null', drop_id=True))
