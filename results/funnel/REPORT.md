# Staged outcome model: measured trial and decision

The feedback deadline cannot be removed without changing the official problem. The practical objective remains more completed dates with recorded timely mutual second-meeting intention, rather than changing the success definition or declaring valid execution a match.

## Implemented

One fixed staged scorer estimates observed mutual introduction acceptance and then auxiliary recorded mutual second-meeting Yes conditional on acceptance. The product is scaled by the training-only timeliness factor. The first head has 32 clean features; the second has 18 goal/post-date-history features. It uses only the 21,367 verified historical introduced pairs, including 3,269 observed mutually accepted introductions and 612 auxiliary positives. The fit uses fixed ridge L2=100 and whole-seed folds. Both predictions enter the unchanged shared asking/matching/availability planner; no priority policy was added.

Official-scaled held-out log loss: 0.05786152, compared with 0.05802407 for the earlier joint model. A repeated fit in a separate directory reproduced identical model bytes. These are selected-cohort diagnostics, not causal or game-win evidence.

## Fresh fixed pilot

New seeds 6301–6302, six families, conservative and staged scorer: 24 episodes, all valid. Both policies had at least one success in 8/12 games. Conservative produced **21 qualifying couples**, staged scorer **9**. The candidate is **rejected for deployment**. Two seed blocks cannot establish a reliable success-rate improvement; 450/480 is not achieved or established. The previous 480-episode confirmation concerns a different scorer and is reported separately.

Family official-couple totals:

| Family | Conservative | Staged scorer |
| --- | ---: | ---: |
| development | 5 | 2 |
| sparse | 0 | 0 |
| cold_start | 3 | 2 |
| delayed | 2 | 2 |
| shift | 6 | 1 |
| drift | 5 | 2 |

The initial evaluation driver counted two completed futures repeatedly. That run is invalid and excluded, not hundreds of independent games. Its raw record, plan and correction explanation are retained. The driver was corrected, and new seeds were registered before restarting; the fitted model and planner were unchanged. Verification now requires the exact 24 unique episode keys. No failed attempt is treated as positive efficacy evidence.

Only the main calibration field in staged pilot rows uses the actual new official-scaled predictions. Other inherited directional/auxiliary calibration fields are reference-harness diagnostics, not evidence for the staged scorer.

## What remains

The active policy stays conservative. The current evidence does not justify deploying either learned replacement. Further progress needs new on-policy training trajectories with point-in-time features and explicit date/response labels, followed by seed-separated whole-game validation. Do not invent outcomes for unchosen pairs or tune against the frozen final worlds. Compare the learned controller with the constant-score control to isolate whether learning helps, and retain waiting/unserved and information-level service slices. The continuation value is still an approximation; this experiment does not solve long-term planning or hidden preference uncertainty.

Native Windows and actual constrained Docker execution remain unavailable here. The existing validation tools must execute on the user's Docker Desktop laptop. Public immutable publication and official submission are separate outstanding actions. No claim that all issues or the desired success rate are solved is supported.

## Supported commands

- Run experimental source: `python3.12 -S -B tools/run_funnel.py < runtime/examples/refreshed_match_request.json`.
- Refit in a separate directory: `python3.12 -B tools/train_model.py --funnel --output ../Staged_Refit`.
- Replay recorded worlds, not independent evidence: `python3.12 -B tools/reproduce_funnel.py --output ../Staged_Replay`.
- Verify release: `python3.12 -B tools/check_release.py`.

The staged model remains research-only and is neither the Docker nor compiled submission entrypoint. No nested ZIPs or priority experiment are included.
