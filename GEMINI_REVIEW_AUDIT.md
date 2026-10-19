# Review audit and submission decision

Checked against the recorded 480-episode confirmation and the pinned organizer simulator. Recompute with `python3.12 -B tools/audit_confirmation.py`. Machine-readable figures are in `results/review_audit.json`.

| Review claim | Verified finding |
| --- | --- |
| 153 zero-score games had mutual Yes but late replies | Correct: these games had at least one auxiliary qualifying mutual-Yes couple, but no official point. This is 153/238 zero-score games, not 64.3% of all couples or all games. |
| 78 failures are caused by trait clashes or hidden second bias | The records establish completed dates without a qualifying recorded mutual Yes. They do not identify all causes. Missing responses or dates outside the scoring window can also prevent a qualifying record. |
| 7 games had no date because scheduling exceeded 30 days | All seven are sparse-family runs. Four had no mutual introduction acceptance; three had acceptance but no completed date. `dates` counts completed dates even outside the 30-day scoring cutoff, so that cutoff does not explain a zero date count. |
| Both answers are timely with probability 36% | Correct under the simulator's independent uniform 1–5-day delay draws, conditional on the relevant recorded mutual Yes. The 153/238 game fraction and the theoretical 64% couple timing-loss probability are different quantities. |
| Five mutual-Yes dates virtually eliminate zero games | The ideal fixed-N calculation leaves a 10.74% zero probability at N=5. N=6 gives 93.13% chance of a point; N=7 gives 95.60%, conditional on the assumptions. N is random in real policy runs; this table does not establish a 450/480 game rate. Maximize qualifying mutual-Yes opportunities, not raw dates regardless of compatibility. |
| 44 fewer dates prove over-deferral | Unsupported causal attribution. Coordinated served 16,195 member-world instances versus 16,168 for conservative, despite 1,978 versus 2,022 dates. The continuation model uses current opportunities, not a future-arrival forecast. Its role needs a controlled ablation. In the earlier small validation, the myopic control scored 3 versus coordinated's 8; that does not support an automatic removal of continuation charges. |
| Episode runtime was 3.04 versus 19.83 seconds | Those are mean policy inference totals. Mean whole-episode wall times were 5.06 and 21.76 seconds. Computation time does not advance the simulator's date clock, though it matters for resource limits and the overall compute budget. |
| Dates must finish before active day 60 | Incorrect. There are 60 decision days plus 40 follow-up days. A day-59 introduction may qualify on a later date within 30 days, with both intentions within three days of that date. |
| Prioritize relationship goal over every other preference | Goal agreement is the only soft attribute directly used in the second-intention probability, but response likelihood, initial acceptance, recorded history and opportunity cost still affect end-to-end success. A fixed override is a hypothesis, not a demonstrated improvement. |
| Relax waiting on days 20–50 | An untested policy change. It was not silently applied or relabeled as a fix. It needs a registered matched full-game ablation with the same official score. |

## Actions completed

The outcome partition and runtime distinction are machine-checked. The scoring deadline, official labels, follow-up window and primary metric remain unchanged. No priority version or nested ZIPs are included. The submission policy remains conservative.

The latest learned trial separates observed introduction acceptance from conditional recorded second-meeting success while retaining one shared planner. It slightly improved training-only held-out loss but lost qualifying-couple count in the fresh pilot: 9 versus conservative's 21, with 8/12 successful games each. It is retained as rejected research and is not deployed. The older 172-versus-170 confirmation is not evidence for this new scorer. See `results/funnel/REPORT.md`.

A SHA-pinned GitHub Actions template is included under `publishing/`, along with archive and native-host receipt utilities. It is prepared, not executed. It checks actual Windows source execution and Linux constrained Docker separately when published in the intended repository; it never promotes a model automatically. These future runs cannot be claimed as passed here.

## Artifact and publication

The quoted `Blackbox_Final1.zip` was not available under that exact name in this session, so its exact-byte identity is not attested. The final archive prepared here is checked independently against its full inventory, SHA-256 and fresh extraction. The ZIP contains project files only, with no previous-version ZIPs or Git metadata.

The organizer's current `docs/SUBMISSION.md` was checked through GitHub (file blob `38fff3045c30571d839b7a86c31b944e0b46a1ab`): deadline 18 October 2026, 23:59 IST; the source/report/results must be in the pinned version. A push and a submission issue are separate actions. No issue has been submitted on the team's behalf.

GitHub push needs the matching-project repository URL and connector access. Only the unrelated OVAEL repository was exposed during preparation; it is not a valid destination for this project. A local commit can be prepared without changing any unrelated repository. Docker/Windows completion and a high success-rate claim remain unverified until their actual evidence exists.
