# Current decision

Conservative remains active. The latest staged-scorer trial is research-only and rejected for deployment: 9 versus 21 qualifying couples in 12 fresh paired worlds, despite a small held-out prediction-loss improvement. Both had 8/12 games with at least one success. The 450/480 target is unproven. See `results/funnel/REPORT.md`. No priority version or nested ZIPs are included.

# Blackbox: Sequential Matching

One current project, no nested ZIPs. The experimental controller uses one success-plus-availability objective for questions, matching and waiting. Its trained 32-feature reward and hold models directly influence decisions.

**Active: conservative. Experimental: coordinated.** See `TECHNICAL_REPORT.md` for all results and failed gates. Windows and constrained Docker execution remain unverified here.

## Run

Use CPython 3.12 (reference 3.12.14). Serving needs only the standard library.

```bash
python3.12 -S -B policy.py --mode conservative < runtime/examples/refreshed_match_request.json
python3.12 -S -B policy.py --mode coordinated < runtime/examples/refreshed_match_request.json
```

On Windows: `cmd /c "py -3.12 -S -B policy.py --mode conservative < runtime\examples\refreshed_match_request.json"`. The compiled alternative is `tools/run_coordinated_compiled.py` with the same two choices. It is CPython bytecode, not a Windows executable.

Carry memory between official ask/match calls and supply actual refreshed observations after questions. Hypothetical answers never become matching permissions.

## Check and reproduce

```bash
python3.12 -B tools/check_release.py
python3.12 -B tools/reproduce_coordinated.py --output ../Blackbox_Replay
```

The first command verifies frozen files, flat training inputs, recorded experiments and planning unit checks. The second creates a separate copy and reruns all 684 fixed comparison episodes under one new two-hour budget. Replays are not new independent evidence. Windows users substitute `py -3.12`.

For deliberate refitting, install `research/requirements-train.txt`, then:

```bash
python3.12 -B tools/train_model.py --verify-data
python3.12 -B tools/train_model.py --output ../Blackbox_Refit
```

Refitting occurs only in a new external copy. Flat collector source/metadata and the compressed JSON observation dataset replace historical ZIP dependencies. Repeating this fit reproduced identical current model/release bytes. Retained old archive-audit scripts are historical source, not current entrypoints. Do not directly refit the frozen release using `coordinated/train.py`.

## Files and evidence

| Path | Purpose |
| --- | --- |
| `coordinated/` | Shared controller, trained models, registered plans |
| `results/coordinated/validation.json` | 84 episodes: three baselines, incumbent, candidate, two ablations |
| `results/coordinated/final.json` | Original 120-episode final, reported separately |
| `results/coordinated/confirmation.json` | Independent fixed-size 480-episode confirmation |
| `results/coordinated/*release_gate.json` | Actual release decisions; no automatic activation |
| `results/coordinated/waiting_times.json` | Served waits, unserved counts, information-level service slices |
| `results/coordinated/transport.json` | 720 cold CLI parity calls on six known worlds |
| `runtime/` | Serving foundation and incumbent assets |
| `research/` | Original executable research source, organizer kit/data, observations, results |
| `evidence/PACKAGE_CLEANUP.json` | Historical snapshot removals and flat-input replacement |

Training seeds: 1101–1148; validation: 4011–4012; original final: 4201–4210; independent confirmation: 5101–5140; known parity replay: 101. No candidate retuning or switching followed these outcomes.

The planner is a bounded approximation, not an exact 60-day optimizer or future-arrival forecast. Selected observations do not establish causal calibration. The constant-model validation control scored 11 versus the learned controller's 8, so learning's added benefit is unproven. See `COORDINATED_DESIGN.md` for assumptions and limitations.

## Runtime and submission

`Dockerfile` serves conservative; `Dockerfile.coordinated` explicitly serves the experimental controller. Neither image was executed here. On your Windows laptop with Docker Desktop running, use `Validate-Windows.ps1` for the active policy. For the candidate, run `python tools/validate_coordinated_container.py --output ../Blackbox_Container_Check`. These commands write external receipts and fail when execution cannot be verified.

`SUBMISSION_MANIFEST.json` binds all files. `tools/freeze_submission.py --output ../Blackbox_Final.zip` creates an immutable ZIP and SHA-256 sidecar. Publish the exact artifact at a version-specific public URL and pin its checksum for official submission. This private download is not that publication. See `CHECKLIST.json`, `SUBMISSION_ISSUE_TEMPLATE.md` and `LICENSING.md`.

## Staged scorer experiment

The current experimental scorer separates mutual introduction acceptance from recorded mutual second-meeting intent conditional on acceptance. Both feed the same unchanged question/matching/availability planner; no priority variant is included. It uses 32 acceptance features and 18 goal/post-date-history conversion features, with fixed ridge L2=100. Official scoring and feedback deadlines are unchanged.

Run `python3.12 -S -B tools/run_funnel.py < runtime/examples/refreshed_match_request.json`. Refit only in a separate new directory with `python3.12 -B tools/train_model.py --funnel --output ../Blackbox_Staged_Refit`. The repeated fixed fit reproduced identical model bytes. This experimental source CLI is not the compiled or Docker submission entrypoint.

Training diagnostics and the fixed fresh 24-episode pilot are in `results/funnel/`; see its REPORT.md for the actual outcome and limitations. The pilot uses seeds 6301–6302 after an evaluation-driver bookkeeping correction; the invalid first attempt is retained and excluded. The 480-episode confirmation still describes the earlier coordinated scorer. Two seed blocks cannot establish superiority or the requested 450/480 rate. Conservative remains active.

Replay just the staged pilot with `python3.12 -B tools/reproduce_funnel.py --output ../Blackbox_Staged_Replay`. It creates a separate copy and new reproduction budget, preserves the authored pilot, and labels replayed worlds as repeated evidence. It does not refit or create independent evaluation worlds.

## Latest review audit and Git publication

`GEMINI_REVIEW_AUDIT.md` separates checked counts from unsupported causal explanations. `tools/audit_confirmation.py` recomputes the outcome partition and runtime figures. The waiting charge was not changed on an arbitrary day schedule. Dates can qualify during the 40-day follow-up. The prepared SHA-pinned CI template is under `publishing/`; no CI, Windows or Docker pass is implied before actual execution. Git push requires the matching-project repository URL and access.
