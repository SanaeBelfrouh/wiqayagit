# Wiqaya — Wildfire risk mapping and alerts for the forests of northern Morocco

**Team:** Wiqaya (Morocco) · **Theme:** Climate & Disaster Resilience · **Arab Youth Space Hackathon 2026, Challenge 813**

**Wiqaya** (وقاية, *"prevention"*) uses free satellite data to map wildfire risk in the Bouhachem, Derdara and
Jbel Sougna forests (about 25,900 ha), **before** a fire starts. The model answers two questions:

- **Where?** Which 250 m patches of the forest are the most fragile.
- **When?** Is today's weather dangerous.

The result is delivered through a trilingual web platform (English, French, Arabic) for the State and for residents.

**Contents:**
1. [Problem](#1-problem)
2. [Users and business model](#2-users-and-business-model)
3. [Data used](#3-data-used)
4. [Model inputs](#4-model-inputs)
5. [Method](#5-method)
6. [Results](#6-results)
7. [Limitations](#7-limitations)
8. [How to run](#8-how-to-run)
9. [Web platform](#9-web-platform)
10. [Next steps](#10-next-steps)
11. [Team, licence and references](#11-team-licence-and-references)

---

## 1. Problem

- **The Rif burns almost every summer.** About 7,500 ha burned in Bouhachem in July–August 2022 [1]. About 1,100 ha
  burned in Sougna, near Derdara, in 2021 [2]. Two fires broke out on 12–13 August 2025, in Derdara and Benqarich [3].
- **Chergui winds raise fire likelihood** in this region [4].
- **445 NASA FIRMS fire detections** fall inside the three forests between 2005 and 2026 [7, 8].
- **The gap:** danger bulletins cover a whole province [5]. Lookouts, thermal drones and satellites only spot a fire
  once it has started [7, 8, 26, 27]. No one knows which 250 m area needs attention today.

## 2. Users and business model

| | |
|---|---|
| **The State** | The National Agency for Water and Forests (ANEF), Civil Protection, the Royal Gendarmerie and local authorities. |
| **The public** | Villagers living in and around the forest, people travelling between the forests, and forest visitors. |
| **What both get** | The same 250 m risk map, the daily danger level, the fire history and the alerts. The public only signs up. |
| **Business model** | Institutions pay a subscription per forest (map, API, alerts). Alerts stay free for residents, paid for by these subscriptions or by CSR partners. |

## 3. Data used

All layers are reprojected to Merchich / Nord Maroc (**EPSG:26191**). Only open data is used: no API key and no imagery cost.

| Layer | Source | Resolution | Period |
|---|---|---|---|
| Active fires | NASA FIRMS, MODIS C6.1 and VIIRS S-NPP 375 m [7, 8] | 375 m – 1 km | 2005-05-09 → 2026-06-05 |
| Terrain | FABDEM V1-2, University of Bristol [9] | 30 m | V1-2, January 2023 |
| Population | WorldPop, Morocco 2017 [6] | 100 m | 2017 |
| Weather | Open-Meteo [30]: Historical Weather API (based on ERA5 [10]) and Forecast API | Hourly | 2005 → today |
| Optical imagery | Sentinel-2 L2A [11] and Landsat Collection 2 Level-2 [12], via Microsoft Planetary Computer | 10 – 30 m | 2005 → 2025 |
| Land cover | 2021 land-cover map of the study area, prepared by the team | 10 m | 2021 |
| Human access | OpenStreetMap roads, tracks, villages and farmland [14] | Vector | 2022 |
| Forest limits | 6-part forest polygon, prepared by the team | Vector | 2026 |

Burned areas are mapped with the dNBR of Sentinel-2 and Landsat images taken before and after each fire [13].

## 4. Model inputs

The forest is divided into **6,071 patches of 250 m**. Each patch receives **16 inputs to know "where"**, and the day
receives **4 weather inputs to know "when"**.

| Source | "Where" inputs per patch |
|---|---|
| DEM [9] | Elevation, slope, aspect |
| DEM and wind [15] | Topoclimate index and its class |
| Land cover 2021 | Land-cover class, flammability |
| Sentinel-2 / Landsat [11–13] | NBR of the last image (taken the day before at the latest) and its trend |
| OpenStreetMap [14] | Human pressure: distance to roads, tracks, villages and farmland |
| WorldPop [6] | Population per patch |
| NASA FIRMS [7, 8] | Fire density and its class, fire power, years since the last fire, burned less than 5 years ago |

| Source | "When" inputs for the day |
|---|---|
| Open-Meteo [10, 19, 30] | Max temperature, min humidity, max wind, max vapour-pressure deficit (VPD) |

Every input and its formula are documented in [`docs/inputs_modele_risque_feu.pdf`](docs/inputs_modele_risque_feu.pdf) (in French).

## 5. Method

**Where? Which parts of the forest are fragile.**
1. **Divide.** One 250 m grid over the six forest parts.
2. **Describe.** Each patch receives its 16 inputs, always computed with data from before the fire day.
3. **Learn.** The model learns, on each fire day, which patches burned and which did not [4, 17]. A patch counts as
   burned when its dNBR shows a burn scar [13].
4. **Map.** Each patch gets a fire probability. KMeans groups close probabilities into **5 risk levels**, with no
   threshold chosen by hand [17]. The riskiest patches become alert zones.

**When? Is today's weather dangerous.**
1. **Measure.** Every day, the 4 weather inputs are read from Open-Meteo [30].
2. **Compute.** The hotter, drier and windier it is, the higher the danger [4].
3. **Compare.** Today is compared with every summer day since 2017.
4. **Alert.** If the danger is high, the alert zones are flagged.

**Honest testing: split by fire, not by patch.** Two nearby patches of the same fire look alike, so mixing them
between training and test would inflate the score [16]. The test fire is always a fire the model has never seen.

| Set | Fires | Patches |
|---|---|---|
| Training (73 %) | 2009 (2 fires), 2020, Derdara 2021 | 24,275, of which 538 burned |
| Validation (27 %), used to choose the model | 2022, Derdara 2025 | 8,871, of which 1,148 burned |
| Test, never seen | Bouhachem near Derdara, 21 August 2025 | 4,905 with a valid image, of which 50 burned |

This split is repeated **12 times**, so that each fire is the test fire twice.

**Four models compared** (scikit-learn [17], Random Forest [18], XGBoost [28], LightGBM [29]), all deliberately
simple because only 8 fires are available. Seed 93.

## 6. Results

**Model choice.** ROC-AUC on the 2022 validation fire:

| Model | ROC-AUC |
|---|---|
| **Logistic regression (selected)** | **0.73** |
| Random Forest | 0.64 |
| LightGBM | 0.63 |
| XGBoost | 0.62 |

Logistic regression is chosen in **10 of the 12 splits**: it stays the best when the test fire changes. With only 8
fires, a simple model learns better than a complex one.

**Test on the Derdara 2021 fire, never seen by the model** (alert on the riskiest 20 % of patches):

| | Model alert | No alert |
|---|---|---|
| **Burned** | 209 found | 52 missed |
| **Did not burn** | 1,006 false alarms | 4,804 correctly classed |

- **Recall 80 %:** the model found 80 % of the burned patches.
- **Precision 17 %:** 17 % of the alerted patches burned, against 4 % of all patches, so 4 times more.
- **ROC-AUC 0.89** on a fire the model never saw.
- Fire is rare: only 4 % of the patches burned, so accuracy is not used.

**Test on the July 2022 fire:** the model's alert covered **41 %** of the burned area.

**Today:** the notebook also computes the risk map of the current day (for example 10 October 2026), with the 5 risk
levels and the weather danger of the day.

## 7. Limitations

- **Few fires.** The model learns from 8 fires only. More fires will make it more stable.
- **False alarms.** Many alerted patches are ready to burn, but no fire started there.
- **Missed patches.** Some fires start from a cause our data cannot see, such as a thrown cigarette.
- **Plant dryness is measured indirectly.** Live fuel moisture needs hyperspectral data (see next steps).

## 8. How to run

Requires **Python 3.11** and an **internet connection** (Sentinel-2 and Landsat are read from Microsoft Planetary
Computer, and the weather from Open-Meteo). The notebook stops with a clear message if there is no connection.

```bash
git clone https://github.com/SanaeBelfrouh/wiqayagit.git
cd wiqayagit
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PROJECT_ROOT="$(pwd)"
jupyter lab notebooks/code207_risque_feu_final.ipynb
```

Run all cells. The notebook writes:
- the maps of each test fire (prediction, evaluation, reality against prediction);
- the susceptibility map and its 5 classes;
- the risk map of the day, as PNG, CSV and GeoPackage;
- the saved model, reused by the platform.

## 9. Web platform

```bash
python server/app.py          # then open http://localhost:8000
```

- **Model:** trained once, then saved on the server.
- **FastAPI server:** takes today's weather from Open-Meteo and computes the map.
- **API:** sends the 250 m patches as GeoJSON, ready for any GIS software.
- **Website:** Leaflet shows the map, the fire history since 2005 day by day, and the SMS / email alert sign-up.
- **Languages:** the site opens in the browser's language (English, French or Arabic, right to left).

The platform runs locally today. Hosting it online is the next step.

## 10. Next steps

1. **More fires:** add fires from other Rif forests, for more examples and a better model.
2. **Hyperspectral:** use EnMAP or Arab Satellite 813 to measure how dry the plants are [20–22].
3. **Go online:** host the site, compute the map every day, send the SMS.
4. **Pilot season:** one full summer with ANEF and local authorities.
5. **Scale up:** other forests in Morocco, then in the Arab region.

## 11. Team, licence and references

**Team Wiqaya, Morocco:**

| Member | Role |
|---|---|
| **Wiame KANE** | Team lead · AI model, geomatics |
| **Sanae BELFROUH** | AI model, API |
| **Yassine AZMOU** | AI model, geomatics |
| **Mohammed Yassine SOF** | Web development |
| **Hajar ELOUATIQ** | Web development |

**Licence.** Code under the [MIT licence](LICENSE). Each dataset keeps its own licence: NASA FIRMS (open, no
restriction), FABDEM (CC BY-NC-SA 4.0), WorldPop (CC BY 4.0), Open-Meteo (CC BY 4.0), Copernicus Sentinel-2
(Copernicus open licence), Landsat (USGS public domain), OpenStreetMap (ODbL).

**References** (same numbering as the presentation):

1. Mongabay (Aug. 2022). Hundreds of iconic Barbary macaques feared dead in Morocco forest fire. https://news.mongabay.com/2022/08/hundreds-of-iconic-barbary-macaques-feared-dead-in-morocco-forest-fire/
2. Médias24 (19 Aug. 2021). Chefchaouen : l’incendie de la forêt Sougna contrôlé, environ 1 100 ha ravagés. https://medias24.com/2021/08/19/chefchaouen-lincendie-de-la-foret-sougna-controle-environ-1-100-ha-ravages/
3. TelQuel (13 Aug. 2025). Incendies : les forêts de Chefchaouen et Tétouan ravagées par les flammes. https://telquel.ma/2025/08/13/incendies-les-forets-de-chefchaouen-et-tetouan-ravages-par-les-flammes_1946474
4. Moumane, A. et al. (2025). Advancing wildfire susceptibility mapping through machine learning and SHapley Additive exPlanations-integrated geospatial analysis in Northern Morocco’s Mediterranean region. Frontiers in Forests and Global Change, 8. https://doi.org/10.3389/ffgc.2025.1705341
5. Hespress (26 Jun. 2023). Incendies de forêts : risque « moyen » à « extrême » dans plusieurs provinces. https://fr.hespress.com/320358-incendies-de-forets-risque-moyen-a-extreme-dans-plusieurs-provinces.html
6. Tatem, A. J. (2017). WorldPop, open data for spatial demography. Scientific Data, 4, 170004. https://doi.org/10.1038/sdata.2017.4
7. Schroeder, W. et al. (2014). The New VIIRS 375 m active fire detection data product: algorithm description and initial assessment. Remote Sensing of Environment, 143, 85–96. https://doi.org/10.1016/j.rse.2013.12.008
8. Giglio, L., Schroeder, W., Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. Remote Sensing of Environment, 178, 31–41. https://doi.org/10.1016/j.rse.2016.02.054
9. Hawker, L. et al. (2022). A 30 m global map of elevation with forests and buildings removed. Environmental Research Letters, 17, 024016. https://doi.org/10.1088/1748-9326/ac4d4f
10. Hersbach, H. et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146, 1999–2049. https://doi.org/10.1002/qj.3803
11. Drusch, M. et al. (2012). Sentinel-2: ESA’s optical high-resolution mission for GMES operational services. Remote Sensing of Environment, 120, 25–36. https://doi.org/10.1016/j.rse.2011.11.026
12. Wulder, M. A. et al. (2019). Current status of Landsat program, science, and applications. Remote Sensing of Environment, 225, 127–147. https://doi.org/10.1016/j.rse.2019.02.015
13. Key, C. H., Benson, N. C. (2006). Landscape assessment (LA). In: Lutes, D. C. et al., FIREMON: Fire effects monitoring and inventory system. USDA Forest Service, Gen. Tech. Rep. RMRS-GTR-164-CD. https://research.fs.usda.gov/treesearch/24042
14. Haklay, M., Weber, P. (2008). OpenStreetMap: user-generated street maps. IEEE Pervasive Computing, 7(4), 12–18. https://doi.org/10.1109/MPRV.2008.80
15. Assali, F. et al. (2016). Modélisation et cartographie du risque d’éclosion d’incendie de forêt dans le nord-ouest du Maroc (région de Chefchaouen-Ouazzane). Revue d’Écologie (La Terre et la Vie), 71(2). https://www.persee.fr/doc/revec_0249-7395_2016_num_71_2_1834
16. Roberts, D. R. et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography, 40, 913–929. https://doi.org/10.1111/ecog.02881
17. Pedregosa, F. et al. (2011). Scikit-learn: machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830. https://jmlr.org/papers/v12/pedregosa11a.html
18. Breiman, L. (2001). Random forests. Machine Learning, 45, 5–32. https://doi.org/10.1023/A:1010933404324
19. Allen, R. G. et al. (1998). Crop evapotranspiration: guidelines for computing crop water requirements. FAO Irrigation and Drainage Paper 56, Rome. https://www.fao.org/4/x0490e/x0490e00.htm
20. Yebra, M. et al. (2013). A global review of remote sensing of live fuel moisture content for fire danger assessment: moving towards operational products. Remote Sensing of Environment, 136, 455–468. https://doi.org/10.1016/j.rse.2013.05.029
21. Guanter, L. et al. (2015). The EnMAP spaceborne imaging spectroscopy mission for Earth observation. Remote Sensing, 7(7), 8830–8857. https://doi.org/10.3390/rs70708830
22. Khaleej Times (11 Dec. 2025). UAE launches first Arab satellite with hyperspectral imaging technology. https://www.khaleejtimes.com/space/arab-satellite-813-launch-successful
23. Hespress (23 Jan. 2025). Forêts du Maroc 2020/30 : une stratégie avec des résultats prometteurs. https://fr.hespress.com/407718-forets-du-maroc-2020-30-une-strategie-avec-des-resultats-prometteurs.html
24. United Nations (2015). Transforming our world: the 2030 Agenda for Sustainable Development. Resolution A/RES/70/1. https://docs.un.org/A/RES/70/1
25. Team Wiqaya (2026). Wiqaya: wildfire risk mapping and alerts. Code, data and results. https://github.com/SanaeBelfrouh/wiqayagit
26. TelQuel (30 Jul. 2026). Incendies de forêt : baisse de près de 31 % des superficies brûlées. https://telquel.ma/instant-t/2026/07/30/incendies-de-foret-baisse-de-pres-de-31-des-superficies-brulees_2001260/
27. Hespress (3 Sep. 2026). Morocco’s northern provinces boost wildfire readiness amid extreme heat. https://en.hespress.com/144795-moroccos-northern-provinces-boost-wildfire-readiness-amid-extreme-heat.html
28. Chen, T., Guestrin, C. (2016). XGBoost: a scalable tree boosting system. Proceedings of the 22nd ACM SIGKDD Conference, 785–794. https://doi.org/10.1145/2939672.2939785
29. Ke, G. et al. (2017). LightGBM: a highly efficient gradient boosting decision tree. Advances in Neural Information Processing Systems, 30, 3146–3154. https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html
30. Zippenfenig, P. (2024). Open-Meteo.com Weather API. Zenodo. https://doi.org/10.5281/zenodo.14582479
