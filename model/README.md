# Research notebook — Fire-risk model, Bouhachem / Jbel Sougna forests (code208)

`code208_risque_feu_autonome.ipynb` is the complete, self-contained research model behind Wiqaya.
Its code comments are in French. The method is summarised in English in the
[main README](../README.md#4-methodology-and-technical-robustness), and every input and formula is documented in
[`docs/inputs_modele_risque_feu.pdf`](../docs/inputs_modele_risque_feu.pdf).

## Inputs

The notebook expects a `data/` folder next to it. All layers are in Merchich / Nord Maroc (EPSG:26191):

| File | Content |
|---|---|
| `limites_forets_26191.*` | Forest boundaries (6 parts) |
| `mnt_bouhachem_26191_30m.tif` | 30 m digital elevation model |
| `occupation_sol_2021_26191_10m.tif` | 2021 land cover, 10 m |
| `population_2017_26191_100m.tif` | WorldPop 2017 population, 100 m |
| `feux_FIRMS/` | NASA FIRMS fire detections (MODIS, VIIRS) |
| `osm/` | OpenStreetMap 2022 roads, tracks, buildings, villages and farmland |

The repository's [`data/`](../data/) folder contains the boundary, DEM, FIRMS and population layers. The 2021 land
cover and the OpenStreetMap layers are not included yet.

## How to run

1. Keep the notebook and the `data/` folder in the same folder.
2. Use Python 3.11. The first cell installs the libraries: geopandas, rasterio, rasterstats, pystac-client,
   planetary-computer, scikit-learn, xgboost, lightgbm…
3. Open the notebook in Jupyter or VS Code and choose **Run all**.
4. An internet connection is required. Sentinel-2 and Landsat images (Microsoft Planetary Computer) and the
   weather (Open-Meteo) are downloaded during the run.
5. The first run takes about 1 h 30 to 3 h. Results are cached in `resultats/`, so later runs are fast.

## Outputs

- `resultats/cartes/`: maps (PNG) and QGIS layers (GeoPackage, EPSG:26191).
- `resultats/calculs/`: intermediate results and the saved model.
- The last cell prints the final summary.
