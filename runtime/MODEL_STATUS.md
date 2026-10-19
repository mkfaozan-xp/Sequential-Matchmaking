# v0.8 measured model status

This runtime preserves the original release and serving bytes. Packaging repair introduces no new training, test-world selection or efficacy evaluation.

| Comparison | Conservative | rank_aux | Scope |
| --- | ---: | ---: | --- |
| Selection pilot | 6 | 9 | 12 worlds, seeds 2953–2954; pilot selection evidence |
| Independent validation | 4 | 11 | 12 worlds, seeds 3051–3052 |
| Frozen final | 36 | 45 | 60 worlds, seeds 3701–3710; 120 paired episodes |
| Subprocess check | 6 | 4 | Six worlds, seed 101; transport check, not a fresh efficacy test |

The final point difference is +0.075 MSMI per 100 arrivals, with a paired seed-block percentile bootstrap interval of [-0.008333333333333333, +0.15833333333333333]. There are ten seed blocks. These are metric units, not percentages; the interval includes zero and is not a power guarantee. The +25% relative count difference is descriptive. Aggregate final outcomes beat or tie the baseline in each of the six families; that does not establish improvement in all worlds or future distributions.

Final family counts (conservative / rank_aux): development 8/9, sparse 2/2, cold_start 5/10, delayed 2/2, shift 11/13, drift 8/9. The statistical promotion criterion and actual container checks remain unmet. The deployment pointer stays conservative; this is an experimental candidate, not a certified winning release.

Training reused 288 recorded collection episodes and 21,367 mature introduced-pair rows; no new collection occurred in v0.8. There are 224 official positive labels and 612 auxiliary positives across the full dataset. Official scoring retains its timely-feedback definition; the auxiliary target separately includes mature late feedback. The selected auxiliary ranking head has 36 active weights. Its fitting loss is an observed-pair ranking measure, not a causal estimate of full-game improvement.

Earlier claims that dropping one missing-value column necessarily repairs ranking are too strong. v0.8 checked reference coding and within-heuristic-score contrasts, but the active auxiliary head still gives a larger relationship-goal missing contribution than agreement. That pattern is disclosed, not declared fixed or proven causal. Zero-effect simulator traits are excluded from the ranking head; original serving heuristics and inherited artifacts remain intact. Any further feature constraint, objective or policy change needs a new frozen experiment and release identity.

The full research archive contains 118 passing core tests, four public-data leakage checks and completed comparison matrices. The prior byte-identical runtime passed 12 complete seed-101 games (six families × two modes, 1,440 restarted CLI calls) against the original subprocess record. This repair rechecks exact serving-byte identity, extracted-package examples and integrity failure cases. Those checks establish the stated scope, not universal absence of leakage, security vulnerabilities or runtime limits.
