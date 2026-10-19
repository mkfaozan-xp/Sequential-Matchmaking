# v0.8 cleaned research profile

This is the original v0.8 research source with redundant inactive release directories removed. All executable source, raw feature/label definitions, current serving assets, training observations, tests, historical archives, source manifests and measured comparison results are retained. The full source/inference identity is unchanged. The original research ZIP is preserved separately and identified in CLEANUP_REMOVALS.json.

Two flat release directories remain: the active immutable release and the earlier source-only packaging-amendment comparator that scripts/audit_review_v08.py reads. Removing that comparator would break a real audit dependency. Training still verifies complete original v0.6/v0.7 archives; do not delete them just because they are large. Historical rollback uses the complete archived version packages rather than the removed flat directories.

Use the original README.md and WINDOWS_START.md for fitting, tests and evaluation. A separate Blackbox_v0_8_Runtime_Clean.zip contains only serving dependencies and one active release for inference. Neither cleanup changes model coefficients, promotes the candidate or creates new efficacy evidence. The v0.8 confidence interval and external-verification limitations remain unchanged.

Extra cleanup validation is saved in results/cleanup_checks.json and cleanup_tests*.json. The original118-test and264-episode evidence remains in its original result files. No full game matrix is rerun or relabelled as new evidence for this packaging change.
