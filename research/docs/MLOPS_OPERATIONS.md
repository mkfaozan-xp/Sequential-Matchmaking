# v0.7 validation and release operations

The current ranking implementation adds a separate ranking-source hash, finite/projection checks and a trained-ranking-assets gate. The observation bundle is included and verified against original v0.6 source/data identities before fitting. Current phases and matrices are bound to new source/assets; older checks remain historical. Default reproduction skips fitting and requires actual conservative and selected-mode containers. The new protocol totals228 current episodes; v0.6 factorial results are archived. Actual counts are in the current report. Prior implementation details below remain applicable except where explicitly historical.

---

# Validation, provenance and release operations

## Separate decisions

| Decision | Required evidence | What it does not establish |
| --- | --- | --- |
| Host workflow completed | Required phases/complete matrices and actual runtime | Docker/Windows compliance |
| Validation ready | Actual tests, checksums, complete baseline pilot and exact assessed image | Better ML policy |
| Candidate eligible | Bound final result, positive lower interval, family/service guards and candidate image | Production certification |
| Externally attested | A real trusted CI attestation over its actual receipt, successfully verified | Truth of every scientific interpretation |
| Release selected | Explicit atomic mode/asset pointer change | Automatic promotion from fitting |

## Local validation

Run scripts/run_tests.py, scripts/environment_report.py, scripts/audit_data.py and scripts/validate_policies.py with the intended interpreter. The bounded run_research workflow includes these checks. Tests report actual counts, inventory checks installed RECORD hashes and licence files, public audit verifies all 71 supplied files, and image assessment executes all six families for each mode. No local signing key is invented to make an unverified run look externally trusted.

Each container build resolves the base tag to an existing verified registry digest and uses PYTHON_BASE=<resolved digest>. It records that subject and assessed image ID. Source, model and sampler remain content-bound. If Docker cannot supply an immutable digest, validation fails rather than silently falling back to a mutable tag.

The inventory is installed-file integrity and licence metadata only. It neither pins every downloadable wheel across platforms nor queries vulnerability databases or grants legal approval. The reference dependencies remain version-pinned; inspect the actual environment.json result.

## Optional CI attestation

The workflow has read-only test/validation jobs and a separate signing job. Only a manual workflow_dispatch with attest=true can enter the signing job, which needs contents:read, id-token:write and attestations:write. It waits for genuine validation, downloads that job's evidence and uses actions/attest@v4 on its ci-receipt.json. The receipt writer refuses missing current tests, inventory/data or actual Docker checks. The attestation signs provenance of the receipt; the receipt hashes the underlying evidence and identifies exact source/assets/mode.

This workflow has not been run merely because this file exists. A private repository may require GitHub Enterprise Cloud for attestations; do not publish a private project as an automatic workaround. Repository creation/publication and actual CI execution are separate actions.

After an actual successful run, download the evidence and verify its receipt, using your trusted repository name:

```bash
gh attestation verify PATH/TO/ci-receipt.json -R OWNER/REPOSITORY
```

Inspect the verified repository, workflow/ref and commit against the intended trusted build, then recompute the receipt's evidence hashes. Do not accept an arbitrary repository's attestation just because a signature validates. Keep the returned verification evidence if asserting external provenance. No signed-ready receipt is called signed before this operation succeeds.

## Scope and resource choices

SQLite plus OS-held locks is appropriate for two local evaluators under an offline CPU protocol. Network shares and multi-host coordination are unsupported. A distributed ledger requires a different backend/ownership design if requirements change; adding a service now would not improve the assessed policy.

Python 3.12.14 is the reference image/runtime. Newer interpreters can run compatibility workflows and are recorded explicitly. CI contains Linux/Windows and 3.12/3.14 test targets, but only actual job results can establish support. Evaluation-cache keys include actual runtime/dependency versions; frozen source/asset plans can be reproduced across environments without relabelling the original execution.

References: [GitHub artifact attestations and entitlement](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations), [Python virtual environments](https://docs.python.org/3/library/venv.html), the pinned starter interface and Docker runner source.


## Current authoring scope

Actual current suite and runtime counts are in results/tests.json and results/runtime.json. The required runtime matrix covers conservative, rank_tie and rank_aux on three shapes and both phases. A pre-pilot broader probe timed out after ten seconds in legacy hybrid_pair_global; its raw failure is retained under evidence/v0_7_first_attempt. That legacy native-solver mode remains unverified. The required call ceiling was not relaxed. The source amendment and same-deadline continuation are explicit.
