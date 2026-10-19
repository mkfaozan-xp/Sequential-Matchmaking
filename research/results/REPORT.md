# Blackbox v0.8 measured review response

Source: `65e2d14ab9d468a902af97ea79780b2523306d7b12b9414ebf7d90e9d5595bf4`.
Release: `2f58302651f1d80bb7990a78654d8598e014e7860bc29c365c195b9881dea7a9`. Active mode: **conservative**.

## Review corrections and implementation

Training now compares actual observed introductions with equal deployed seven-field agreement scores, within the same world and seven assignment days. The model is still only an ordinal tie-breaker. Reference coding and removal of post-date history are explicit alternative models. Neither coding change nor a negative history coefficient independently establishes a defect or a cause of the earlier pilot loss.
Reference coding removes four missing dummies:36 → 32 features. Removing 16 post-date inputs additionally leaves 16. Changing the dummy basis changes ordinary ridge regularization, not an automatic monotonicity guarantee. Constant translation of history rates cancels in differences; the raw history implementation and smoothing prior are preserved. A rate of 0.5 does not imply no prior date.
Official MSMI labels, timing rules, RNG and simulator remain unchanged. Late mutual recorded Yes is auxiliary evidence, not a replacement official outcome. The exact v0.7 auxiliary coefficients are retained as a historical unmatched-training control, excluded from eligible candidates. Its older selection differs, so this is not a pure causal ablation of every mechanism.

## Training provenance

Reused 288 historical collection episodes and 21367 mature observed introductions, with 224 official and 612 auxiliary positives. **New collection episodes:0.**
Archive, source, payload, raw feature/label definitions and ordered row identities are verified. No padded vectors or unchosen labels are used. Whole training seeds remain in one fold. The older probability heads and answer prior are explicitly inherited.

| Head | Dimensions | Contrasts | Positive introductions represented | Estimator | Nonzero weights |
| --- | ---: | ---: | ---: | --- | ---: |
| rank_official | 36 | 1672 | 207 | constant_prevalence, L1=0, L2=None | 0/36 |
| rank_auxiliary | 36 | 4386 | 549 | ridge_logistic, L1=0, L2=100 | 36/36 |
| rank_reference | 32 | 4386 | 549 | ridge_logistic, L1=0, L2=100 | 32/32 |
| rank_nohistory | 16 | 4386 | 549 | constant_prevalence, L1=0, L2=None | 0/16 |
| rank_legacy_aux | 36 | 6010 | 611 | ridge_logistic, L1=0, L2=100 | 36/36 |

Mirrored contrasts are dependent transformations, not new independent games. Equal scores and nearby days do not establish competing endpoints, simultaneous availability, population validity or known propensities. Selection bias remains.

The historical mismatch was reproduced: 1904/3005 auxiliary comparisons cross heuristic-score levels. The new cohort has 2193 forward equal-score comparisons. All recorded new training contrasts have equal actual heuristic scores.
Equivalent reference recoding of the old model changed logits by at most 2.22e-16 across all 21367 rows. This refutes a guaranteed coding-only cure.

## Verification

Core tests: 118; passed: True. Public snapshot: True; runtime inventory: True.
Cold runtime probes: 36 across all six pilot modes; maximum measured startup/call time 0.466s. The original ten-second limit is unchanged.
Complete cold/cached action parity: True; preparation seed 1999,200 members, conservative and rank_ref. These four preparation episodes are not efficacy comparisons.
Separate public-data leakage checks are recorded in phase logs. Trusted host caching is bounded and invalidates on observed hard-field changes. Cold CLI inference and final action validation remain uncached. Host checks and Docker recipes do not certify Docker, Windows, hosted CI or external signing.

## Frozen choice

Selected **rank_aux** on pilot seeds [2953, 2954], before independent validation and final outcomes. Selection uses official MSMI, then question cost, then lexical mode. No post-pilot refit/switch occurs.

## Selection pilot

Saved 72 / 72; complete and valid: **True**; failed attempts: 0.

| Mode | Introductions | Mutual acceptances | Dates | Official MSMI | Auxiliary mutual Yes |
| --- | ---: | ---: | ---: | ---: | ---: |
| conservative | 804 | 119 | 95 | 6 | 30 |
| rank_tie | 804 | 119 | 95 | 6 | 30 |
| rank_aux | 789 | 129 | 110 | 9 | 33 |
| rank_ref | 802 | 124 | 105 | 6 | 30 |
| rank_nohistory | 804 | 119 | 95 | 6 | 30 |
| rank_legacy | 801 | 126 | 107 | 7 | 31 |

## Independent validation

Saved 60 / 60; complete and valid: **True**; failed attempts: 0.

| Mode | Introductions | Mutual acceptances | Dates | Official MSMI | Auxiliary mutual Yes |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_greedy | 934 | 108 | 90 | 4 | 20 |
| baseline_no_asks | 232 | 30 | 29 | 0 | 8 |
| baseline_random | 904 | 99 | 76 | 5 | 21 |
| conservative | 934 | 107 | 89 | 4 | 20 |
| rank_aux | 914 | 98 | 84 | 11 | 22 |

## Frozen final

Saved 120 / 120; complete and valid: **True**; failed attempts: 0.

| Mode | Introductions | Mutual acceptances | Dates | Official MSMI | Auxiliary mutual Yes |
| --- | ---: | ---: | ---: | ---: | ---: |
| conservative | 4708 | 675 | 504 | 36 | 113 |
| rank_aux | 4705 | 668 | 493 | 45 | 120 |

Paired seed-block result: `{"status": "descriptive_seed_block_bootstrap", "seed_blocks": 10, "delta": 0.075, "ci95": [-0.008333333333333333, 0.15833333333333333], "warning": "Descriptive percentile bootstrap; sample count alone does not establish statistical power."}`.

| Family | Conservative MSMI | Candidate MSMI |
| --- | ---: | ---: |
| development | 8 | 9 |
| sparse | 2 | 2 |
| cold_start | 5 | 10 |
| delayed | 2 | 2 |
| shift | 11 | 13 |
| drift | 8 | 9 |

Identical action traces: 1/60 paired worlds. Ten seed blocks are a minimum, not a power guarantee. Different version totals on different worlds cannot establish an improvement. Reference-head calibration diagnostics are separate from ordinal ranking utilities.


## Fresh-process transport

Saved 12 / 12; complete and valid: **True**; failed attempts: 0.

| Mode | Introductions | Mutual acceptances | Dates | Official MSMI | Auxiliary mutual Yes |
| --- | ---: | ---: | ---: | ---: | ---: |
| conservative | 528 | 91 | 78 | 6 | 20 |
| rank_aux | 521 | 98 | 81 | 4 | 20 |

## Release decision

Readiness: **blocked**. Missing/failed checks: `['exact_container_release']`.
Candidate promotion assessment: `{"checks": {"exact_candidate_container": false, "minimum_seed_blocks": true, "no_family_mean_regression": true, "positive_paired_lower_bound": false, "service_guardrail": true, "validation_readiness": false}, "eligible": false, "evaluated": true, "family_scores": {"conservative": {"cold_start": 0.25, "delayed": 0.1, "development": 0.4, "drift": 0.4, "shift": 0.55, "sparse": 0.1}, "rank_aux": {"cold_start": 0.5, "delayed": 0.1, "development": 0.45, "drift": 0.45, "shift": 0.65, "sparse": 0.1}}, "paired_interval": {"ci95": [-0.008333333333333333, 0.15833333333333333], "delta": 0.075, "seed_blocks": 10, "status": "descriptive_seed_block_bootstrap", "warning": "Descriptive percentile bootstrap; sample count alone does not establish statistical power."}, "reason": "Predeclared gates; 10 blocks is a minimum guardrail, not a statistical-power guarantee", "scenario_guardrail": true, "service_guardrail": true}`.
No automatic promotion. The active operational mode remains conservative.

## Budget

Status at report generation: completed. The original v0.8 allocation is 7200s, with one retained deadline across retries. Exact phases/failures are in budget_run.json.
This is a new user-requested build. Earlier v0.6/v0.7 accounting remains unchanged historical evidence; their cap was not retroactively reset. Code preparation/packaging are outside the model execution allowance. In v0.7, 1390s was the initial allowance;825s described a resumed invocation, not the whole allocation.

## Remaining limits

A favorable pilot, contrast loss or nominal final advantage does not guarantee policy superiority. Rare outcomes, selected-label bias and long-horizon availability effects remain. No new asking/allocation factorial is claimed; v0.6 research remains historical. Production certification, real-world relationship prediction and private-world superiority are not established. Actual Docker, Windows, hosted CI and trusted external attestation remain required unless their executed records explicitly establish them.


## Completed authoring disposition

All 264 declared host comparison episodes are complete and valid, plus 118 core tests, 4 separate public-data leakage checks, 36 cold runtime probes and 4 preparation parity episodes. The original v0.8 deadline was retained through the documented packaging repair. The interrupted first pilot 2951–2952 is preserved separately; current comparisons use fresh2953–2954. Fitted coefficients were verified unchanged by that source-only repair. The clean ZIP excludes the live deadline marker; authoring origin is retained in evidence and budget records.

Actual Docker, Windows, hosted CI and external signing remain unperformed. Conservative is still active. No current review issue is reported as a proven cause of an earlier loss or as a guaranteed ML victory.

## Remaining fitted preference behavior

| Current head | Goal agree | Goal disagree | Goal missing |
| --- | ---: | ---: | ---: |
| rank_auxiliary | -0.002515 | -0.354141 | 0.356655 |
| rank_reference | -0.111639 | -0.473947 | 0.000000 |

Both fitted auxiliary variants still give goal agreement a lower partial contribution than missingness. Reference coding does not impose monotonicity; no such constraint was added. This behavior is disclosed, not labelled repaired by deleting a column. Complete pair ordering also includes the primary seven-field heuristic and other features. Coefficients alone do not establish which legal choice caused a final success or loss.
