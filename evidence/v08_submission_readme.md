# Blackbox — complete Round 2 submission package

**Submitted policy: conservative.** The root Dockerfile fixes this mode in both the environment and entrypoint. The experimental `rank_aux` score is reported separately and is not the submitted score. This is distribution revision 2 of the existing v0.8 model release; serving algorithms and weights are unchanged.

This revision also includes a verified **CPython 3.12 compiled build**. Read `COMPILED_BUILD.md` for execution and rebuild commands. On Windows: `cmd /c "py -3.12 -S -B tools\run_compiled.py --mode conservative < runtime\examples\refreshed_match_request.json"`. The trained JSON weights and original complete research sources are retained.

This archive includes the full cleaned research project, reproducible training/evaluation code, original results and logs, all three supplied baselines, a direct asking ablation, and a standalone runtime. Actual Windows and constrained Docker execution remain open on the authoring host. `CHECKLIST.json` and `submission.json` report that status explicitly.

| Location | Purpose |
| --- | --- |
| `TECHNICAL_REPORT.md` | Submitted policy, baseline comparison, scenario metrics, waiting times, ablation and limits |
| `results/submitted_policy_final.json` | All 60 recorded final episodes for conservative: 36 official successes |
| `research/results/validation.json` | All three supplied baselines, conservative and experimental candidate on the same 12 worlds |
| `results/asking_ablation.json` | 24 executed episodes removing asking while holding allocation fixed |
| `results/first_introduction_waiting_times.json` | Raw served waits, unserved counts, exposure and information-level service slices |
| `research/` | Complete 590-file research snapshot: scripts, data, plans, evidence, tests and dependencies |
| `runtime/` | Verified standalone serving profile with immutable assets and example checks |
| `evidence/current_checks/` | New 118-test record, diagnostic execution logs and actual host capabilities |
| `SUBMISSION_MANIFEST.json` | Frozen inventory and per-file SHA-256 values |

## Inspect and run

Extract the ZIP and open a terminal in `Blackbox_Round2_Submission`. Reference interpreter: Python 3.12.14. Serving, package inspection and container validation need only Python's standard library and Docker where applicable.

WSL/Linux:

```bash
python3.12 -B tools/verify_submission.py
python3.12 -S -B runtime/verify_runtime.py --smoke
python3.12 -S -B runtime/policy.py --mode conservative < runtime/examples/refreshed_match_request.json
```

Native Windows PowerShell:

```powershell
py -3.12 -B tools/verify_submission.py
py -3.12 -S -B runtime/verify_runtime.py --smoke
cmd /c "py -3.12 -S -B runtime\policy.py --mode conservative < runtime\examples\refreshed_match_request.json"
```

The official interface is restart-per-call JSON on stdin/stdout. Preserve returned memory and use refreshed observations after questions. No web interface is required to execute the policy.

## Close Windows and Docker checks

Install Python 3.12 and start Docker Desktop with Linux containers/WSL2 integration. In native Windows PowerShell, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Validate-Windows.ps1
```

This checks native default-mode execution, builds the **root** Dockerfile using a resolved base registry digest, verifies immutable image ID/mode/assets, and runs six complete 200-member seed-101 games using the unchanged organizer harness. Each policy invocation has the official 10-second timeout. Containers use no network, read-only rootfs, 2 CPUs, 1 GiB RAM and swap cap, 64 PIDs, a 64 MiB tmpfs, dropped capabilities and UID/GID 65534. No organizer data or source directories are mounted. The image limit is 2 GiB. The whole command has a retained 120-minute invocation budget; it fails on unmet prerequisites or mismatched/invalid episodes.

Evidence is saved in a new sibling directory, never inside this frozen tree. Reruns use new evidence directories and are separate recorded executions, not additional independent worlds. A Linux-only execution cannot establish the native Windows check. No passing Windows or Docker result is bundled or implied by this delivery. Preserve the external receipt and its immutable image ID if the checks pass.

For a manual build, use `docker build -t blackbox-round2:submission .` from this top-level folder. The root image is the submitted policy. Do not build the experimental runtime Dockerfile and label its candidate results as conservative.

## Reproduce research in a working copy

Keep the delivered ZIP and extracted frozen tree intact. Copy the `research` folder to a separate working location before rerunning its workflows; they intentionally create logs, ledgers and results. Python training dependencies are exactly `numpy==2.3.5` and `scipy==1.17.0`, pinned in `research/requirements-train.txt`. On Linux/WSL, from that working research copy:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-train.txt
.venv/bin/python scripts/run_tests.py
.venv/bin/python starter/verify_data.py
.venv/bin/python official_data_training/test_leakage.py
.venv/bin/python evaluate.py --seeds 3051,3052 --variants all --methods baseline_greedy,baseline_no_asks,baseline_random,conservative,rank_aux --jobs 2 --output results/reproduced_validation.json
```

On Windows use `py -3.12 -m venv .venv` and `.venv\Scripts\python.exe` for the subsequent commands. The supplied baselines are called through the original `starter/policy.py`; the project root policy's similarly named modes are not substituted for those controls.

To replay the new direct asking ablation without modifying the submission:

```bash
python3.12 -B tools/reproduce_ablation.py --output ../Blackbox_Ablation_Replay/asking_ablation.json
```

That diagnostic uses previously observed validation worlds and is not new independent efficacy evidence. It did not tune or select the final policy. Original full pilot/final commands, frozen plans, collection/refit provenance and the original retained two-hour build budget remain in `research/README.md`, `research/plans/` and `research/results/`. Refitting is a new experiment, not required to run the shipped release. Do not tune on the recorded final seeds or overwrite closed evidence.

Training collection seeds are 1101–1148 across six families (288 historical episodes; no new collection). Pilot: 2953–2954. Validation/asking diagnostic: 3051–3052. Final: 3701–3710. Transport checks: 101. Conservative inference is deterministic; the supplied random baseline uses `17 + day`.

## Freeze and submit exact bytes

The companion `.zip.sha256` file gives the exact delivered archive digest. Verify it before uploading. `tools/freeze_submission.py` can re-export unchanged verified contents to a new external path and writes its own checksum; a new export must use that export's digest.

The official instructions, fetched on 17 October, close final submission on **18 October 2026 at 23:59 IST**. They require a public repository pinned to a full commit SHA or an immutable public archive URL with its full SHA-256. This private download is not an organizer submission or a public source URL. Publish the exact ZIP as a version-specific release asset, include its digest and report/results links in the official Final submission issue, and do not replace it after the deadline. See `SUBMISSION_ISSUE_TEMPLATE.md`.

Any changed content requires a new archive/checksum and pre-deadline pin. The checksum cannot be embedded inside the same ZIP it hashes, so it is supplied separately. Local manifests and image hashes are not external digital signatures. Read `LICENSING.md` and preserve upstream terms when publishing.
