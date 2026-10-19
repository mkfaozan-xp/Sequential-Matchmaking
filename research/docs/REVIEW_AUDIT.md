# v0.8 disposition of the Gemini reviews

Both supplied review texts are retained under evidence/reviews. Historical results remain historical; current measurements are in results/REPORT.md and results/review_audit.json.

| Claim or issue | Verified disposition | Implementation |
| --- | --- | --- |
| Auxiliary model trained across score levels despite tie-only deployment | Confirmed:1,904/3,005 historical auxiliary forward comparisons cross actual heuristic scores | Require equal seven-field agreement count, world and nearby assignment day; verify every contrast |
| Dropping missing is an automatic one-line repair | Incorrect guarantee: equivalent reference coding preserves predictions and the missing/agree ordering | Fit separate full 36 and reference32 models with explicit penalty/schema metadata; numerical equivalence audit |
| Missing coding had28 features after dropping four columns | My earlier audit label was wrong;36-4=32 | Correct documentation, tests and actual schema; no-postdate reference has 16 |
| Negative history weights prove the cause of the pilot loss | Not established from selected survivor cohorts or coefficients | Preserve point-in-time history semantics; add retrained reference/no-postdate control |
| Recenter history at 0.35 to fix survivor bias | A constant translation cancels in contrasts; changing a smoothing prior is a distinct unvalidated hypothesis | Do not hardcode an empirical universal prior; compare removing post-date features |
| second_yes_rate0.5 means no prior date | False: observed dates with no answered second feedback or balanced answers can also yield0.5 | Add a semantic regression and retain separate date/response/no-history features |
| Retirement occurs after mutual recorded Yes | Confirmed in public simulator | Preserve simulator and observed-history policy; do not claim a causal survivor correction |
| Coding/history effects explain exactly three fewer pilot successes | Unproven without an appropriate controlled experiment; twelve worlds are limited | Fixed new model controls and independent final comparison; no final-driven changes |
|611 auxiliary positive examples were newly collected | They are represented historical positives among612 raw auxiliary positives, not new independent games | Zero new collection; export matched represented-positive counts |
| V0.7 had only 825s initially | Incorrect: initial allowance1390s;825s was one resumed invocation | Preserve historical records and disclose the separately bounded new build |
| A constant head learned to decide when to stop guessing | Model selection chose a constant competitor; this is not a learned abstention mechanism | Explicit estimator/nonzero-weight exports and unchanged conservative default |
| More regularized/ranking signal guarantees game improvement | False; loss targets, selected cohorts and sequential availability differ | Official MSMI remains primary; strict paired/family/service/container gates |
| Repeated compatibility checks consume CPU | Confirmed by preserved v0.7 profile | Bounded trusted-host memoization, complete public-input fingerprints, live action checks, invalidation and parity tests |
| A passed host pipeline certifies Docker/Windows/CI | False | Explicit unverified records until actual execution; no fabricated signatures |

All older regularization, auxiliary-label and point-in-time date-history implementations remain preserved. Official labels, lateness, simulator RNG and raw feature definitions are unchanged. Earlier v0.5/v0.6/v0.7 scores are not directly compared as improvement because their worlds differ. See the embedded original v0.7 ZIP for the complete earlier audit and releases.

A pre-final packaging review caught a live-deadline marker in the proposed archive. The marker is excluded from clean packages and retained in authoring evidence; retry source checks bind the current pilot subject. The partial2951–2952 pilot is preserved and replaced by fresh2953–2954 under the same v0.8 deadline, without outcome-driven model changes.

## Delivered verification

The implementation passed118 core tests, 4 additional leakage checks, 36 runtime probes, four full cold/cached preparation episodes and 264 complete host comparison episodes. See results/REPORT.md for the actual candidate, final outcome, uncertainty and failed promotion conditions. Docker/Windows/hosted CI/trusted signing remain unverified; no local hash is represented as an external signature.
