# Round 2 technical submission report

Submitted policy: **conservative**, release `2f58302651f1d80bb7990a78654d8598e014e7860bc29c365c195b9881dea7a9`. The root Dockerfile fixes the same mode in its environment and entrypoint. `rank_aux` remains an experimental comparison; its 45 final successes are not the submitted policy score. No policy or coefficients were changed for this distribution.

## Method and reproducibility

The policy asks to resolve unknown reciprocal hard constraints, prunes questions where a known hard failure already rules out a pairing, then selects feasible non-repeated pairs greedily by observed soft agreements. Unknown values are not inferred as hard approvals. The observable request is the policy input; simulator hidden fields stay on the engine side. The policy is deterministic and uses no inference RNG. The supplied random-feasible control uses seed 17 + day. Training seeds 1101–1148, six families, belong to inherited research artifacts; conservative does not use their learned ranking coefficients. Inference requires Python standard library only; fitting uses Python 3.12.14, NumPy 2.3.5 and SciPy 1.17.0 on CPU.

## Supplied baselines on identical worlds

Validation contains 12 worlds: seeds 3051–3052 × six families, 200 members, 60 decision days and 40 follow-up days each. Full machine-readable episodes and scenario summaries are in research/results/validation.json. These are previously measured worlds, not new independent trials.

| Mode | Official MSMI | First dates | Coverage | Served wait mean / p95 days | Unserved instances | Ask cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_greedy | 4 | 90 | 0.327 | 7.14 / 21.00 | 1615 | 2559 |
| baseline_no_asks | 0 | 29 | 0.117 | 2.80 / 13.00 | 2119 | 0 |
| baseline_random | 5 | 76 | 0.330 | 6.67 / 20.00 | 1609 | 2559 |
| conservative | 4 | 89 | 0.327 | 7.09 / 21.00 | 1615 | 2529 |
| rank_aux | 11 | 84 | 0.325 | 6.30 / 18.00 | 1619 | 2529 |

Conservative ties greedy and trails random by one success in this small validation comparison. No claim that it dominates the supplied baselines is supported. High coverage alone does not imply higher MSMI.

## Submitted-policy frozen final, scenario detail

| Family | Worlds | Official MSMI | First dates | Coverage | Served wait mean / p95 days | Unserved instances | Ask cost | Missing feedback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 10 | 8 | 108 | 0.399 | 6.94 / 26.00 | 1202 | 1914 | 493 |
| sparse | 10 | 2 | 27 | 0.166 | 6.65 / 20.00 | 1669 | 1944 | 107 |
| cold_start | 10 | 5 | 71 | 0.344 | 8.66 / 24.00 | 1313 | 2331 | 413 |
| delayed | 10 | 2 | 100 | 0.394 | 6.79 / 25.00 | 1212 | 1914 | 461 |
| shift | 10 | 11 | 97 | 0.397 | 6.69 / 24.40 | 1207 | 1914 | 469 |
| drift | 10 | 8 | 101 | 0.399 | 6.94 / 26.00 | 1202 | 1914 | 491 |

Across 60 worlds (seeds 3701–3710), conservative records 36 official successes and 504 first dates; score 0.3000 MSMI per 100 arrivals. Coverage is 0.3496; served-only mean first-introduction wait is 7.126 days and p95 is 24.300 days. There are 7805 unserved member-world instances out of 12000. Unserved waits are right-censored, not zero. Total unserved exposure is 441971 days. The raw waits, counts and information-level service slices are included in results/first_introduction_waiting_times.json.

Recorded host inference totals 175.549 seconds over these episodes. These trusted in-process measurements do not estimate fresh-container startup or Windows performance. Missing-feedback counts above use the unchanged kit definition; missing or late feedback is not silently relabeled as official success.

## Hypothesis-driven asking ablation

Hypothesis: removing pruned hard-field clarification while holding the observed-soft-score greedy allocator fixed changes feasible service and official MSMI. We declared and executed conservative versus the existing no_asks mode on validation seeds 3051–3052 across six families (24 episodes). This post-review diagnostic reuses observed worlds, is not a fresh efficacy test and did not select or change the final policy. All 12 conservative action traces and reported outcomes exactly reproduce the original controls.

| Policy | Official MSMI | Served instances | Unserved instances | Ask cost |
| --- | ---: | ---: | ---: | ---: |
| conservative | 4 | 785 | 1615 | 2529 |
| no_asks | 0 | 281 | 2119 | 0 |

The observed contrast supports the usefulness of asking on these worlds. It does not prove allocation-aware asking or complementary endpoint questions outperform simpler rules. Earlier ranking/reference/history ablations and the original closed protocols remain in the research package with their limits.

## Validation and remaining limits

All 118 core tests passed again on this Linux/Python 3.12.14 host. The reviewed runtime retains 20 byte-identical serving/source/asset files and prior 12-game subprocess parity evidence. This assembly adds packaging and metric checks; it does not reset the original closed experiment or invent fresh independent populations.

The experimental rank_aux final score was 45 versus 36, with paired seed-block interval [-0.0083333, +0.1583333] MSMI per 100 arrivals. Its positive-lower-bound gate fails; conservative stays active. Ranking utilities are not calibrated outcome probabilities. Reference probability diagnostics are in the original report, not relabeled as calibration of the submitted heuristic.

Native Windows and constrained Docker remain unverified because this authoring host has neither Windows nor a Docker CLI/socket. Validate-Windows.ps1 executes both on available hardware, pins the base/image digest, verifies the default mode, uses the organizer harness for six complete offline 200-member games and writes external evidence without changing this archive. It fails on missing prerequisites or invalid episodes. Container validation and a version-specific public archive URL plus checksum are still required before submission.

Source/model/data/tool provenance, original experiment plans, training logs and upstream licences are retained under research/. No private organizer worlds, credentials or real-member data are added. The original two-hour research budget remains untouched; the additional declared diagnostic took 54.802 seconds and no new model training. Rare outcomes, simulator assumptions, repeated-world diagnostics and delayed feedback limit generalization.

## Compiled-build revision

Distribution revision 2 adds CPython 3.12 checked-hash bytecode for all 134 runtime/research Python files. Two independent reference-environment builds were byte-identical. The compiled loader executed every loaded blackbox module from bytecode while retaining source paths for the original release-integrity checks. All 640 model outputs on 64 recorded feature vectors and all six example policy responses matched the source implementation exactly. Twelve complete seed-101 transport games, covering both modes and all six families, reproduced every action and compared outcome across 1,440 restarted compiled-policy calls. This is functional parity on recorded worlds, not new efficacy evidence or a claim of faster inference. Original research/runtime sources, weights and final policy remain unchanged. See COMPILED_BUILD.md and evidence/compilation/. Native Windows and Docker checks remain open.
