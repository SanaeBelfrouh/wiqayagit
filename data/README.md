# Example input data (`data/sample_input/`)

Small inputs clipped to the area of interest (AOI): the Bouhachem, Derdara and Jbel Sougna forests in northern Morocco,
about 25,900 ha. Everything is in Merchich / Nord Maroc (EPSG:26191). Total size: 8.4 MB.

| File | Content | Source and processing |
|---|---|---|
| `forest_boundaries.gpkg` | Forest boundaries, 6 parts (`part` = a to f) | GIS layer prepared by the team |
| `dem_30m.tif` | Digital elevation model, ~25 × 31 m pixels, float32 (m) | DEM prepared by the team, clipped to the forest plus 1 km |
| `population_2017_100m.tif` | Population count per 100 m pixel | WorldPop 2017 `mar_ppp_2017` (unconstrained, 3 arc-seconds), clipped to the forest plus 10 km and reprojected to 100 m with sum resampling (totals kept within 0.1 %) |
| `firms_fire_detections.gpkg` | 1,176 active-fire detections within 5 km of the forest, 2005-05-09 to 2026-06-05 | NASA FIRMS archive download for the AOI: MODIS Collection 6.1 (2005–2017) and VIIRS S-NPP 375 m Collection 2 (2017–2026). Fields: `ACQ_DATE`, `ACQ_TIME`, `SATELLITE`, `INSTRUMENT`, `CONFIDENCE`, `FRP` |

The weather used by step 7 of the notebook and by the web platform is downloaded at run time from Open-Meteo. It needs no API key.
