# v0.8 frozen review-response protocol

This new user-requested build has its own maximum 7,200-second execution allowance. Earlier v0.6/v0.7 budgets and their incomplete/blocked results remain unchanged historical evidence; this is not a continuation pretending to fit the earlier cap. Setup, fitting, checks and evaluation share one v0.8 deadline. Preserve interruptions and do not shrink matrices after outcomes.

## Confirmed issue and hypotheses

V0.7's auxiliary contrasts include 1,904 cross-heuristic-score comparisons out of 3,005. The deployed ranker only changes equal-score edge ordering. New contrasts must have the same observed seven-field heuristic agreement count, same world seed/family and assignment days within seven days. Use at most five deterministic observed negatives per positive, then mirror differences. Equal scores do not imply the pairs competed for an endpoint, were available simultaneously or have known propensities. No causal, counterfactual or IPS claim is made.

Dropping a redundant missing dummy is a parameterization/regularization experiment, not a guaranteed repair. Full one-hot has36 dimensions; reference coding drops four missing columns to32; additionally removing16 post-date history inputs leaves16. Reference missing is zero and agreement coefficients can still be negative. Do not hardcode coefficients or monotonicity from the inspected pilot. Constant translation of history rates cancels in contrasts. Do not alter the established raw feature/history code, smoothing prior, official labels, simulator, timing rules or RNG. Test removal of post-date history instead of inventing a universal survivor mean.

## Fitting and controls

Reuse exactly the verified v0.6 dataset:288 historical collection episodes,21,367 observed mature pair rows,224 official and612 auxiliary positives. Zero new collection. Verify archive/source/payload/schema/ordered-row lineage as in v0.7. All actual rows in each contrast are recorded chosen introductions; no unchosen labels are invented. Eligibility for matched negatives may reduce represented positives; export counts rather than claiming all612 were used. Keep complete seeds in six train-only folds. Compare identity logistic ridge L2=10/100, elastic net L1=2/L2=10 and a constant, selecting equal-seed contrast log loss with unchanged convergence checks.

Fit four heads: official/full36 (rank_tie), auxiliary/full36 (rank_aux), auxiliary/reference32 (rank_ref), auxiliary/reference/no-postdate16 (rank_nohistory). All share score-matched construction, grid, folds and deterministic negative ordering. Compare full/reference regularization and post-date history as model/input ablations; cross-validation scores on differing constructed cohorts are not independent policy evidence. Preserve the exact v0.7 auxiliary head as rank_legacy for an unmatched-construction historical control, excluded from eligible candidates. Its dataset and earlier selection differ; this control does not isolate every causal mechanism. Inherit older probability heads/answer prior explicitly, separate their calibration diagnostics from ordinal utilities.

All five ranking modes use unchanged pruned hard questions, soft agreement +0.25*sigmoid(rank_logit), greedy legal allocation and cold standard-library inference. Strict heuristic gaps cannot be reversed. Deployment stays conservative; fitting and selection never auto-promote.

## Fixed matrices

Pilot2953–2954, all six families, modes in order conservative/rank_tie/rank_aux/rank_ref/rank_nohistory/rank_legacy:72 episodes. Eligible candidates are the four matched learned modes, including constant fallback. Choose highest official MSMI mean, then fewer question units, then lexical mode. Keep the choice even if every learned candidate loses; freeze source/assets/mode before independent evaluation. No final-driven refit/switch/extension.

Validation3051–3052:three supplied baselines, conservative and selected candidate,60 episodes. Final3701–3710:conservative/candidate,120 episodes,200 arrivals,60 decision days and40 follow-up. Fresh subprocess101:conservative/candidate,12 episodes. Total264 comparison episodes. Earlier final ranges through3601–3610 remain consumed/reserved as recorded, with v0.7's unexecuted final explicitly historical. No new asking/allocation factorial is claimed; v0.6's study remains historical.

Same fresh worlds are shared across methods; uncertainty uses ten final seed blocks, not episodes as independent subjects. Promotion requires strict positive paired lower interval, no family mean regression, service guards, current tests/data/runtime and actual baseline/selected-candidate Docker assessments. No external evidence is manufactured from configuration.

## Execution optimization and checks

At most two episode workers and single numerical threads. Trusted host episodes use verified, scoped model/prior snapshots and a bounded20,000-entry cache of public hard-eligibility results. Prepare keys from member_id/pool_id/age/gender/zone and all11 observed hard fields; availability, past pairs and final action checks remain live. Updated hard observations invalidate entries by fingerprint; copies prevent caller mutation; clear the cache at scope exit and at the bound. Standalone CLI and subprocess paths do not enter these scopes. Do not change domain.py or the official simulator for speed.

Before pilot, run regression checks for missing-reference equivalence, actual seven-field score matching, feature schemas/no-history isolation, history-centering interpretation and cache invalidation/bounds. Check complete cold/cached200-member action parity on preparation seed1999/development for conservative and rank_ref; preparation worlds are not efficacy evidence. Runtime probes cover all six pilot modes, three shapes and two phases:36 cold CLI calls with the original ten-second limit. No requirement is relaxed when a check fails. Record pre-pilot repairs; if source changes after pilot inspection, preserve attempts and declare new reservations before retrying.

Actual Docker, Windows, hosted CI and trusted external signing require their own execution. If unavailable, host results may be complete while release readiness remains blocked. Package source, exact fitted assets, observations, all phase evidence, historical archives and the review audit.

## Reproduction-boundary amendment

The first partial pilot2951–2952 is preserved without using its outcomes to change scores or model parameters. Source inspection caught a packaging defect: the active workflow deadline marker must not be shipped as a live marker in a clean reproduction. Exclude results/workflow_origin.json from the ZIP; keep its full contents in budget evidence and archive the authoring marker separately after execution. Guard retries against the actual pilot source rather than the initial source before an explicitly recorded repair. Refit identical declared models/checks under the amended source and use fresh pilot2953–2954. Final3701–3710 remains unseen. The original v0.8 deadline is retained, including failure, authoring and restart gaps.
