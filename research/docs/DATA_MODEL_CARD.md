# v0.8 data and model card

Task: synthetic sequential reciprocal matching under delayed observed feedback. Primary endpoint remains qualifying completed meeting plus timely mutual second-meeting intention per100 arrivals. Auxiliary recorded mutual Yes includes late feedback only in its separate mature cohort; it does not change official scoring.

Data: the exact v0.6 observation bundle, 288 historical episodes, 48 training seeds 1101–1148 across six families, 21,367 introduced-pair rows, 224 official and 612 auxiliary positives. No new collection. Original ZIPs, source/payload identities, schema and ordered rows are verified. Official public training responses remain in the inherited directional task; validation/development-test records are not fitted into main heads.

Models: four matched-score relative logistic heads with 36/36/32/16 inputs and an inherited historical36-input auxiliary control. Constant fallback remains eligible. Six whole-seed folds compare fixed ridge/elastic-net penalties. Mirrored contrast rows are dependent transformations, not additional independent successes. Actual cohort sizes and represented positives are recorded in results/training.json.

Risks: selected introductions, unknown action propensities, retirement survivor bias, profile disclosure patterns, rare outcomes, world/day trajectory sensitivity and shift. Equal-score matching does not identify counterfactual utility. An observed negative history slope is not proof of bias removal or a preference defect. Calibration JSON refers to inherited probability heads, not ordinal action utilities. This synthetic model is not validated for real relationships.

Review-source corrections and current outcomes are in docs/REVIEW_AUDIT.md and results/REPORT.md. Conservative remains deployed until complete promotion evidence and an explicit justified release action.
