# Research notebook — full fire-risk model (code208)

`code208_risque_feu_autonome.ipynb` is a standalone variant of the research model behind Wiqaya. The final
model is in [`notebooks/02_main_analysis.ipynb`](../notebooks/02_main_analysis.ipynb).

The research notebook needs more inputs than the repository ships: a 2021 land-cover raster and OpenStreetMap distance
layers. It also downloads Sentinel-2 and Landsat scenes from Microsoft Planetary Computer, which takes about 1 h 30 to
3 h on the first run. Its code comments are in French. Every input and formula is documented in
[`docs/inputs_modele_risque_feu.pdf`](../docs/inputs_modele_risque_feu.pdf).

## What it contains

- **Spatial "fire day" model.** It is trained on 8 documented fires between 2005 and 2022, comparing burned and
  unburned cells of the same day. Burned areas come from the Sentinel-2 or Landsat dNBR (threshold 0.27, FIRMS mask,
  checked against the official burned areas). The two 2025 fires are kept as a blind test.
- **29 inputs**, including NDVI, NDMI and NBR (with their trends), flammability from land cover, the topoclimate index
  (Assali et al., 2016), human pressure from OpenStreetMap, and fire-history density and power.

## How to run

1. Put a `data/` folder next to the notebook, with these files:
   - `limites_forets_26191.*`
   - `mnt_bouhachem_26191_30m.tif`
   - `occupation_sol_2021_26191_10m.tif`
   - `population_2017_26191_100m.tif`
   - `feux_FIRMS/`
   - `osm/osm_code13_2022_distance_*.parquet`
2. Use Python 3.11. The first cell installs geopandas, rasterio, rasterstats, pystac-client, planetary-computer,
   scikit-learn, xgboost and lightgbm.
3. Choose **Run all**. Results are written to `resultats/cartes/` (maps and GeoPackages) and `resultats/calculs/`.

Planetary Computer is used anonymously: no API key is needed.
