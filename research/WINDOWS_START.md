# Blackbox v0.8 Windows / WSL2 guide

Extract Blackbox_ML_Prototype_v0_8_Clean.zip and open Blackbox_ML_Prototype. Reference runtime is Python 3.12.14. Use Docker Desktop Linux containers with WSL integration. Prefer the WSL Linux home filesystem; no unmeasured speedup is promised. Actual Windows/Docker/newer-Python execution has not been performed in this authoring environment.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Blackbox.ps1 -Minutes 120
.\Start-Blackbox.ps1 -Minutes 120 -Python 'C:\Path\To\python.exe'
```

```bash
python3.12 scripts/run_research.py --bootstrap --minutes 120 --skip-training
```

The launcher creates .venv and preserves shipped fitted assets. WSL uses .venv/bin/python; Windows uses .venv\Scripts\python.exe. Do not move environments between operating systems. -HostOnly / --skip-docker cannot validate a submission sandbox. Read results/REPORT.md for actual host results and unresolved gates.

## Reproduction and evidence

The archive excludes live ledgers, training caches and host environments. It includes the verified compressed observation bundle needed for refitting, fitted JSON assets, all current measurement JSON and retained historical releases. Clean extraction therefore reruns comparisons rather than claiming cache hits are new independent observations.

- results/training.json and model_selection.json: actual cohort counts, grouping and fitted heads.
- results/review_audit.json: measured review checks, equivalent reference recoding and historical mismatch.
- results/selection.json and plans/final_test.json: frozen candidate, source/assets and final 3701–3710.
- results/budget_run.json and workflow_origin.json: one deadline and actual phase status for this build.
- results/container_attestation.json / container_candidate.json: real container evidence or explicit unverified status.
- docs/REVIEW_AUDIT.md: issue dispositions and remaining limits.

Keep artifacts/final_seed_registry.json. Source or policy changes after pilot inspection require a newly declared experiment; never tune against frozen final outcomes. Earlier v0.7 final 3601–3610 was unrun but reserved. Roll back using the complete embedded v0.7 ZIP; keep source and assets together.

Docker assessment must actually run conservative and the selected candidate across six families with verified base/image identity: no network, read-only rootfs, 2 CPUs, 1 GiB memory, 64 PIDs, 64 MiB temp and a2 GiB image ceiling. Host timing and Docker recipes are not certification. Hosted CI and trusted external signing require real execution.

OS-held locks release on process death; do not delete live lock files. A retry retains the same workflow deadline and audit trail. The v0.8 build is separately bounded; previous iteration budgets remain unchanged historical evidence. Conservative stays active unless a separately justified release action occurs.

Clean packages exclude the live workflow deadline marker; authoring origin remains archived in evidence and budget_run.json. A fresh reproduction creates its own declared build deadline. An interrupted local build still retains its original marker and cannot silently reset it.
