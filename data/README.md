# Example input data (`data/sample_input/`)

Small inputs clipped to the area of interest (AOI): the Bouhachem, Derdara and Jbel Sougna forests in northern Morocco,
about 25,900 ha. Everything is in Merchich / Nord Maroc (EPSG:26191). Total size: 8.4 MB.

| File | Content | Source and processing |
|---|---|---|
| `forest_boundaries.gpkg` | Forest boundaries, 6 parts (`part` = a to f) | GIS layer prepared by the team |
| `dem_30m.tif` | Digital elevation model, ~25 × 31 m pixels, float32 (m) | FABDEM V1-2 (University of Bristol, Copernicus GLO-30 with forests and buildings removed, https://doi.org/10.5523/bris.s5hqmjcdj8yo2ibzi9b4ew3sn), reprojected to EPSG:26191 and clipped to the forest plus 1 km. Licence CC BY-NC-SA 4.0: this clipped file is shared under the same licence |
| `population_2017_100m.tif` | Population count per 100 m pixel | WorldPop 2017 `mar_ppp_2017` (unconstrained, 3 arc-seconds), clipped to the forest plus 10 km and reprojected to 100 m with sum resampling (totals kept within 0.1 %) |
| `firms_fire_detections.gpkg` | 1,176 active-fire detections within 5 km of the forest, 2005-05-09 to 2026-06-05 | NASA FIRMS archive download for the AOI: MODIS Collection 6.1 (2005–2017) and VIIRS S-NPP 375 m Collection 2 (2017–2026). Fields: `ACQ_DATE`, `ACQ_TIME`, `SATELLITE`, `INSTRUMENT`, `CONFIDENCE`, `FRP` |

The weather used by the web platform is downloaded at run time from Open-Meteo. It needs no API key.

## Inputs of the main notebook

[`notebooks/02_main_analysis.ipynb`](../notebooks/02_main_analysis.ipynb) uses the team's working folder
`data_prepared/reprojete_26191/` when it is present at the repository root:

| File | Content |
|---|---|
| `limites_forets_26191.shp` | Forest limits, 6 parts |
| `mnt_bouhachem_26191_30m.tif` | DEM resampled to 30 m |
| `population_2017_26191_100m.tif` | WorldPop 2017, 100 m |
| `feux_FIRMS/fire_*.shp` | NASA FIRMS points (3 files) |
| `occupation_sol_2021_26191_10m.tif` | 2021 land-cover map of the study area, 10 m |
| `osm/osm_code13_2022_distance_{route,piste,batiment,douar,agriculture}_m.parquet` | OpenStreetMap 2022 layers |

Without this folder, it reads the four files above instead, plus `land_cover_2021_10m.tif` and
`osm/osm_code13_2022_distance_*_m.parquet` placed in this folder. The forest and FIRMS files are the same: the
notebook rebuilds the same 6,071-cell grid and finds the same 445 FIRMS points inside the forest (1,176 within 5 km).
The DEM here keeps its original 25 m pixels and the terrain values differ slightly (mean slope per cell 23.8 % instead
of 23.2 %; mean elevation within 0.1 m), so the scores are close to, but not exactly, the recorded ones.

To reproduce exactly the recorded results, the notebook also reuses the team's caches, placed at the repository root:

- `data_prepared/code89_risque_feu_aujourdhui/cache/` (`static.parquet` and the daily `fenetres/*.parquet`): the 20
  days without fire are drawn from these days;
- `data_prepared/code201_risque_feu_2005_2022_jbelsougna/cache/fenetres/` and `.../cache_dnbr/`: the satellite
  values of each fire day and the dNBR burned areas. Missing days are recomputed from Microsoft Planetary Computer,
  which takes 1 h 30 to 3 h.
