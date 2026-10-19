# Official public-data training companion

Run from the project root after installing the pinned training dependencies:

```bash
python official_data_training/train_public.py
python official_data_training/test_leakage.py
python -S official_data_training/predict_response.py < examples/refreshed_match_request.json
```

On Windows, use `py -3.12` or the interpreter in the project environment. Fit runs with the existing NumPy/SciPy dependencies. Both the main submitted policy and the new diagnostic inference entry point use only the standard library. The diagnostic accepts the existing refreshed match request and emits individual response estimates for up to ten legal pairs in input order. It does not select actions or multiply two dependent responses into an unsupported joint MSMI probability.

This companion actually fits records supplied in the organiser's repository. It is separate from the fixed simulator-policy experiments, which use newly collected point-in-time rollouts from that same public simulator. Its fit does not modify the main release, final plan or deployment pointer. Its helper source is part of the executable source identity, so changing that code invalidates existing source-bound evidence. The archive manifest covers this companion; its fitted model also records its own training-source and input hashes.

## Inputs and split discipline

Official repository: https://github.com/RomeoJulietLove/The-Sequential-Matching-Problem

Verified default-branch head: `a8e26b35118cfa8e886a02f93984923e43ab64f6`.

All 70 bundled data files and `data_manifest.json` match GitHub blob identities exactly. The bundled Python reference files and checksum JSON have one additional trailing newline; their Python ASTs / parsed checksum values are identical. See `evidence/official_sources/local_comparison.json` for the exact byte comparison, including these differences. No public data was replaced or regenerated.

| Role | Pools | Use |
| --- | --- | --- |
| Train | public_01–public_06 | Fit response head and empirical clarification donors |
| Validation | public_07–public_08 | Report diagnostics after the training-only choice |
| Development-test | public_09–public_10 | Not opened by this training workflow |

The supplied Drive folder is titled **IITM || RJ || Workshops**. Its seven listed items are workshop PDFs, a PPTX, a DOCX and two videos. The listing contains no train/test data files or child folders. The host's README states that the complete public dataset is already in GitHub `data/`; private organiser worlds are absent. The Drive inventory is preserved under `evidence/official_sources/drive_folder.json`. Workshop prose is not treated as tabular training examples.

## What was fitted

`results/response_model.json` is a regularized logistic head for **recorded introduction acceptance**, including a recorded nonresponse as no acceptance. This is a different outcome from mutual second-meeting intention (MSMI); it is not a preference or psychological label. It uses the 76 directional observable features, including point-in-time date and second-intention history, with an optional declared nonlinear basis.

The fitter uses only introduction cohorts whose response deadline has passed at day 30. Every mature actor must have exactly one visible response event. Pending cohorts are excluded even when one actor responded early. It retains only profile fields whose recorded observation day is at or before assignment, and history visible at that decision. It excludes feedback from the target introduction from predictive history. A later reconfirmation is conservatively masked; this can lose earlier information but cannot copy a later value backward. The reference v1 generator uses static field truths in these public pools; this assumption is source-specific and must be reviewed for a different dataset. Day-30 conversations and questionnaires are never joined backward.

Selection compares the predeclared identity, compact, signal-projection and interaction ridge/elastic-net grid and a constant predictor using whole-training-**pool** grouped log loss (six folds for these six pools). No validation row enters fitting or selection. `model_selection.json` retains every fold and candidate. There are only six training pools and two validation pools; row count is not the number of independent worlds.

`results/answers.json` additionally fits an empirical distribution of 787 complete observed hard-field bundles from the six training pools. These are disclosed bundles, not unbiased population samples. They are suitable only as an experimental hypothetical clarification prior; they never replace actual observed eligibility or override a refusal. No outcome or propensity is invented.

## Measured result and deployment

The current fit uses only the six declared public train pools. Read current counts, selected estimator and validation metrics from `results/training_report.json` and fold choices from `results/model_selection.json`. V0.5's 658 training records, 204 validation records and AUROC0.459425 are historical measurements, not evidence for the new feature schema.

Artifacts remain `experimental_not_deployed`. The main policy separately merges public train directional records and donors with new rollout training; it does not use this companion's validation rows. Conservative remains the operational default. No private-test or production-readiness claim follows from these diagnostics.

Four passing regression checks cover future-disclosure invariance, exclusion of pending cohorts with early positive responses, future-feedback feature invariance and non-mutating evaluation. Refit from the same checked input to reproduce the artifact; do not overwrite a held-out split to improve validation numbers.

## v0.6 measured companion result

The current fit retained 658 mature training responses (246 recorded Yes) and 204 validation responses (80 Yes), selecting the signal projection with elastic net L1=2,L2=10. Validation AUROC is 0.512903, but log loss0.672293 still exceeds the constant baseline0.670414. The ranking metric alone is not evidence of improved calibration or MSMI gameplay. This diagnostic remains experimental and separate from main deployment.
