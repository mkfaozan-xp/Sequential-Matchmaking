# Blackbox v0.8 — reviewed standalone runtime

Default: **conservative**. The experimental **rank_aux** candidate is available for explicit comparison and has not been promoted. This is a repaired distribution of the existing v0.8 release; no model was retrained and no serving algorithm was changed.

Extract the ZIP, open a terminal in `Blackbox_Runtime`, then verify and run it. Reference interpreter: Python 3.12.14. These two modes use only the standard library; no pip install is needed.

WSL/Linux/Bash:

```bash
python3.12 -S -B verify_runtime.py --smoke
python3.12 -S -B policy.py --mode conservative < examples/refreshed_match_request.json
python3.12 -S -B policy.py --mode rank_aux < examples/refreshed_match_request.json
```

Windows PowerShell, with CMD handling input redirection:

```powershell
py -3.12 -S -B verify_runtime.py --smoke
cmd /c "py -3.12 -S -B policy.py --mode conservative < examples\refreshed_match_request.json"
cmd /c "py -3.12 -S -B policy.py --mode rank_aux < examples\refreshed_match_request.json"
```

Send one official JSON request on stdin; actions go to stdout and diagnostics to stderr. Carry returned memory into the next request. After asks, submit the engine's refreshed observation for matching. `day0_request.json` and `empty_request.json` are additional examples. This is an engine policy, not an interactive matchmaking interface.

## What this package supports

Only `conservative` and `rank_aux` are documented and checked for this distribution. Other original CLI modes remain in byte-identical serving code for provenance, but are outside this package's supported profile. In particular, native solver modes may need third-party dependencies. `requirements.txt` is a comment-only dependency declaration, not a pinned training environment.

The immutable release includes its model, answer reservoir and manifest. All are kept because release verification binds their bytes. The reservoir is a disclosed inherited training artifact, not an organizer test-data bundle. Package inventory and golden example hashes are in `RUNTIME_MANIFEST.json`; run the verifier after extraction. These hashes detect accidental changes and are not external signatures. `PRIOR_EPISODE_PARITY.json` is the prior 12-game parity record for the identical serving files; `VERIFICATION.json` distinguishes inherited evidence from this repair's new checks.

Training scripts, evaluation supervisors, unit suites, nested historical ZIPs, datasets and experiment logs are omitted here. Keep `Blackbox_ML_Prototype_v0_8_Clean.zip` separately for research and reproducibility. Its historical archives have live training/audit dependencies; deleting them blindly breaks that workflow. No commands in this runtime require files from that archive.

## Model status

See `MODEL_STATUS.md` for measured results and `REVIEW_RESPONSE.md` for corrections to the supplied Gemini review. The final candidate scored 45 versus 36 official successes; the paired interval includes zero. Its six-family subprocess check scored 4 versus 6. Conservative remains active. Do not change deployment mode or edit byte-bound model/source files while treating the old evidence as certification of the change.

## Container recipe

The original Dockerfile is unchanged and all its COPY inputs are included. Example WSL/Bash commands:

```bash
docker build -t blackbox-runtime .
docker run --rm -i --network none --read-only --cpus 2 --memory 1g --pids-limit 64 --tmpfs /tmp:size=64m blackbox-runtime < examples/refreshed_match_request.json
```

For an explicit experimental container, build a separate tag with `--build-arg POLICY_MODE=rank_aux`. These commands were not executed here. Docker Desktop/Windows execution, sandbox resource limits, hosted CI and external signing remain unverified. A recipe or local SHA-256 check does not establish container attestation. Use the full research workflow to collect those checks before an official submission. Newer Python interpreters may be tried, but this delivery was checked only on the recorded reference interpreter.
