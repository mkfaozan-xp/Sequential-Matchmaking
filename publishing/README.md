# Publish one exact ZIP

The prepared Git repository contains one `Blackbox_Submission.zip`, its checksum, a short index and this CI template. It does not put any previous-version ZIP inside the submission ZIP.

The publisher places `verify-submission.yml` at `.github/workflows/verify-submission.yml` and the two Python utilities at `ci/`. Actions are pinned to verified upstream commit SHAs. The matrix extracts the exact archive, installs pinned development dependencies, tests native Windows and Linux source execution, and runs constrained baseline Docker games on Linux. Windows source execution and Linux Docker evidence are distinct. Neither is claimed to have run merely because the template exists. No model is automatically promoted.

Use the destination project repository, preserving its visibility and branch policies. After pushing, inspect successful receipts and pin the exact commit/archive SHA in the organizer's Final submission issue before the deadline. A prepared local commit is not a remote push, and a push is not an official submission. This task does not create an organizer issue.
