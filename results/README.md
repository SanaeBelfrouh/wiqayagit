# Results

Figures and tables produced by [`notebooks/02_main_analysis.ipynb`](../notebooks/02_main_analysis.ipynb), taken from
its recorded outputs. The figure titles are still in French: they were drawn before the notebook was translated, and
they will be in English after the next full run.

## Headline figure

- `example_output.png`: July 2022 fire (validation, never seen by the model). Left: area that actually burned (dNBR).
  Right: the model's alert on the riskiest 20 % of cells, which covered 41 % of the burned area.

## Spatial model ("where?")

| File | Content |
|---|---|
| `splits_12_results.csv` | The 12 fire-based splits: test and validation fires, selected model, ROC-AUC, PR lift, recall, precision |
| `splits_mean_by_test_fire.csv` | Mean scores for each test fire (each fire is the test fire twice) |
| `model_comparison_validation.csv` | Logistic regression, Random Forest, XGBoost and LightGBM on the 2 validation fires |
| `presented_split_summary.csv` | Split shown in the maps: test = Bouhachem near Derdara 2025; validation = Derdara 2025 and 2022 |
| `confusion_*.csv` | Confusion matrices of these 3 fires (alert = riskiest 20 % of cells) |
| `class_balance_by_fire.csv` | Burned and unburned cells for each fire |
| `feature_importance.csv`, `feature_importance.png` | Absolute standardised coefficients of the final logistic regression |
| `test_2025_bouhachem_near_derdara_*.png` | Test fire: 1 prediction, 2 evaluation, 3 predicted risk and measured dNBR, 4 reality and alert |
| `validation_2025_derdara_*.png`, `validation_2022_*.png` | The same 4 maps for the 2 validation fires (`validation_2022_4` is `example_output.png`) |

## Annual susceptibility (FIRMS 2017-2024, tested on 2025)

| File | Content |
|---|---|
| `susceptibility_leave_one_year_out.csv` | Validation with one whole year left out at a time |
| `susceptibility_test_2025.csv` | Independent test on the 2025 FIRMS points and burned areas |
| `susceptibility_2025_map.png` | Susceptibility on 1 August 2025 and years since the last fire |
| `susceptibility_test_2025_*.png` | Burned area against the 20 % most susceptible cells, for each 2025 fire |

## Weather danger ("when?") and map of the day

| File | Content |
|---|---|
| `weather_danger_fire_days.csv` | Weather danger index of the 8 fire days, against 976 summer days 2017-2024 |
| `risk_map_2026-10-10.png` | Risk map of 10 October 2026: fire probability per cell and the 5 KMeans risk levels |
