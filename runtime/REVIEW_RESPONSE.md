# Response to the supplied Gemini runtime review

## Findings and changes

The uploaded runtime's 31 files all matched their counterparts in the measured research release. No altered model weights or serving logic were found. Its README was copied from the research package and instructed users to run absent scripts, PowerShell launchers and training commands. That is a concrete packaging defect.

This repair replaces those instructions with self-contained Windows and WSL commands, documents the supported two-mode boundary, corrects the dependency declaration, adds an executable standard-library verifier and golden response hashes, and includes accurate model status and validation evidence. It adds LF checkout settings for Windows Git users. The unreferenced environment-report helper `blackbox/runtime.py` and non-serving `artifacts/candidate.json` status duplicate are removed; their hashes are recorded in VERIFICATION.json. Neither is a Docker COPY input or serving dependency. The serving entry point, 15 required modules, deployment pointer and three release artifacts remain byte-identical to the measured build. The Dockerfile is unchanged.

## Claims checked against source and results

| Supplied claim | Finding and disposition |
| --- | --- |
| “Unambiguous” win across every matrix | Overstated. Pilot 9–6, validation 11–4 and final 45–36 favor rank_aux; the subprocess transport matrix is 4–6. The final paired interval includes zero. Kept conservative active. |
| Lower bound misses zero by “less than 1%” | The interval is in MSMI per 100 arrivals, not percent. A small numerical distance is not evidence that a gate should be bypassed. Corrected units and uncertainty. |
| v0.7 ZIP is completely unused | False. scripts/train_rankers.py loads its frozen legacy auxiliary head; scripts/audit_review_v08.py reads it. Retained in research, omitted only from runtime. |
| v0.6 ZIP is needed only for a hash | False. The trainer reads its model, answer reservoir and training configuration, validates collector source, row order and dataset ancestry. The gzip snapshot does not replace these checks. Retained in research. |
| Historical logs are all dead or exact duplicates | Overbroad. scripts/audit_review_v08.py reads prepackage-amendment evidence; historical records preserve closed run identities. The completed-host-results folder is not an exact copy of today's results directory. Runtime does not ship these folders. |
| official_data_training is unused | False for research: scripts/run_research.py runs its training and leakage checks. It is outside this runtime's serving path. |
| More than 20 dead modes should be deleted | Inactive for this two-mode runtime does not prove unused by research controls, collectors or tests. Preserve measured serving bytes and explicitly limit the supported profile; removing branches requires a new source identity and validation. |
| requirements.txt contains pinned dependencies | False: the uploaded file contains comments only and points to absent requirements-train.txt. Replaced with an accurate standard-library declaration. |
| Two CLI probes establish production readiness or zero leakage | Unsupported. They show limited example execution. New checks verify file integrity and example parity; actual Docker, Windows, CI and external signing remain unverified. |
| Size values labeled MB | Several quoted figures use 2^20 bytes and should be MiB. Exact output sizes are recorded in the delivery receipt; runtime and research profiles have different purposes. |

## Scientific limits

No training, simulator formulas, official label definitions, split seeds, selection thresholds or promotion gates were changed for this packaging task. The missing-versus-agree ranking pattern is still present and is not a proven one-line bug. Feature removal alone is not a guaranteed performance fix. Historical evaluation worlds must not be reused as fresh evidence after tuning.

The original closed-build records and full research archive are preserved separately. Local checksums are integrity evidence, not signed attestation. A smaller serving archive does not imply faster inference or a certified production deployment.
