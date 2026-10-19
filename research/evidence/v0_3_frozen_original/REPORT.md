# Blackbox v0.3 - engineering and ML evidence

All outcomes are synthetic. Validation is distinct from candidate promotion and production readiness.

## Build changes

- Strict typed hard constraints and observable timestamps; malformed hard fields fail before matching.
- Content-addressed training caches bind generator, collection policy, feature/label code and runtime version.
- Model and answer sampler are published together in an immutable, hash-verified release directory.
- Deployment selection and rollback are atomic pointer changes; fitting does not imply promotion.
- SQLite ownership leases, heartbeats, stale-owner rejection and append-only attempt history.
- Tests, validation matrices, frozen plans and Docker attestations bind exact code and inference assets.
- Windows/WSL runner supervises child processes within a requested maximum 120-minute budget.
- Test-pass counts are read from real test results, never hardcoded.

- Hard-killed episode owners recover through OS-held owner locks without a lease wait; legacy owners retain lease fallback.
- Docker base-image preparation precedes training; baseline and learned container assessments precede validation, with downstream reservations.
- Joint and directional regularization use leave-one-training-seed-out selection; final-test outcomes never enter fitting.
- Promotion requires independent learned-policy container evidence, in addition to statistical and service gates.

## Current identity

Release: `729ca785dcb175066ad9f209e08882385cf8c4386c175ca0fcac1873e309a796`.
Model: `logit-e09e7dda795ecd55`.
Full source/configuration: `153f3ae756683b3484721be78a5bc53d2cada84c6a0bf2f3f6e698c03be7051e`.

## Training

Bundle model training rows: 3385; positive MSMI outcomes: 53.
Training lineage and package versions are embedded in the immutable release manifest. Imported v0.1 assets are identified explicitly when applicable.
Training evidence covers 48 episodes; training-pipeline wall time (cache reuse may apply) 244.2 seconds.

Training-only regularization selection (equal seed weight):

| Head | L2 | Seed-held-out log loss | Constant-prevalence log loss |
| --- | --- | --- | --- |
| joint | 100 | 0.081442 | 0.081457 |
| direction | 100 | 0.659760 | 0.659369 |

These are predictive diagnostics on selected introductions, not evidence that the policy improves MSMI.

## Tests and data

Actual tests run: 70; success: True.
- project: 48 tests, 0 failures, 0 errors, 0 skipped.
- starter: 22 tests, 0 failures, 0 errors, 0 skipped.
Public-byte checksum verification: passed for 71 files.

## Policy validation

Episodes present: 120 / 120; complete: True; all valid including prior failed attempts: True.
Methods share worlds. Repeated policy runs are executions, not independent populations. Confidence intervals resample seed blocks.

| Method | MSMI pairs | MSMI per 100 | Coverage |
| --- | --- | --- | --- |
| baseline_greedy | 15 | 0.3125 | 33.35% |
| baseline_no_asks | 13 | 0.2708 | 12.71% |
| baseline_random | 16 | 0.3333 | 33.62% |
| conservative | 15 | 0.3125 | 33.35% |
| learned | 18 | 0.3750 | 33.40% |

Learned-minus-conservative paired pilot result: `{"status": "descriptive_seed_block_bootstrap", "seed_blocks": 4, "delta": 0.06249999999999999, "ci95": [-0.25, 0.25], "warning": "Descriptive percentile bootstrap; sample count alone does not establish statistical power."}`.
A pilot does not establish statistical power or justify test-seed tuning.

Per-family pilot scores (MSMI per 100):

| Family | Conservative | Learned |
| --- | --- | --- |
| development | 0.5000 | 0.5000 |
| sparse | 0.0000 | 0.0000 |
| cold_start | 0.1250 | 0.2500 |
| delayed | 0.2500 | 0.6250 |
| shift | 0.5000 | 0.3750 |
| drift | 0.5000 | 0.5000 |

## Container and release state

Container evidence: unverified.
Validation gate: blocked.
Attestation records bind local content hashes and immutable image IDs. They are not digitally signed certificates.
No candidate is automatically promoted by this workflow. The default remains conservative.
The Docker image must run on the Windows/WSL2 host before Docker/resource compliance can be claimed. Hosted CI and native PowerShell execution are not inferred from supplied configuration.

## Remaining research limits

- Rare positive labels, selective collection and simulator transfer remain unresolved statistical issues.
- The answer model is a selected empirical bundle approximation, not unbiased exact EVSI.
- Equal-compute complementary-question tests and controlled allocation tie ablations remain necessary.
- A larger frozen final test is not automatically included in the two-hour pilot budget.
- Episode JSON includes mature feature missingness, score quantiles, calibration and service slices by family; selective labels still limit interpretation.
- Base-image digest pinning and a full third-party dependency-license audit remain release-hardening tasks.

Prior v0.1/v0.2 evidence is archived under evidence and is not counted as v0.3 verification.

## Frozen final test

Complete: True; valid: True; episodes: 120.
Paired learned-minus-conservative result: `{"status": "descriptive_seed_block_bootstrap", "seed_blocks": 10, "delta": 0.10833333333333334, "ci95": [2.7755575615628915e-18, 0.23333333333333334], "warning": "Descriptive percentile bootstrap; sample count alone does not establish statistical power."}`.
Ten seed blocks meet the minimum gate count; this does not establish adequate statistical power.

Promotion assessment: `{"checks": {"exact_learned_container": false, "minimum_seed_blocks": true, "no_family_mean_regression": false, "positive_paired_lower_bound": true, "service_guardrail": true, "validation_readiness": false}, "eligible": false, "evaluated": true, "family_scores": {"conservative": {"cold_start": 0.3, "delayed": 0.45, "development": 0.45, "drift": 0.45, "shift": 0.6, "sparse": 0.05}, "learned": {"cold_start": 0.15, "delayed": 0.4, "development": 0.8, "drift": 0.85, "shift": 0.7, "sparse": 0.05}}, "paired_interval": {"ci95": [2.7755575615628915e-18, 0.23333333333333334], "delta": 0.10833333333333334, "seed_blocks": 10, "status": "descriptive_seed_block_bootstrap", "warning": "Descriptive percentile bootstrap; sample count alone does not establish statistical power."}, "reason": "Predeclared gates; 10 blocks is a minimum guardrail, not a statistical-power guarantee", "scenario_guardrail": false, "service_guardrail": true}`.
