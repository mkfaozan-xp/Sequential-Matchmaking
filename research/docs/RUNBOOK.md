# v0.8 runbook

Start with WINDOWS_START.md and the shipped fitted assets. Run `python scripts/run_research.py --bootstrap --minutes 120 --skip-training`. The launcher supplies these arguments correctly. --skip-docker is host debugging and leaves release readiness blocked.

Inspect results/budget_run.json, selection.json, raw matrices and REPORT.md. Retry an interrupted build only with unchanged source/assets/configuration and the retained original deadline. Preserve lock/owner directories; OS-held locks release after process death. Do not delete live locks, rewrite failed attempts or count cache reuse as new independent evidence.

If changing source after inspected pilot outcomes, preserve the attempt and declare a new experiment with appropriate fresh reservations. Never refit/switch against final outcomes. Roll back with the complete embedded v0.7 archive, keeping source and model together.

Actual Docker/Windows/CI/external signing require independent execution. Treat a constant selected head, nonpositive uncertainty bound, family regression or service failure as evidence against promotion. The active mode remains conservative even after fitting.
