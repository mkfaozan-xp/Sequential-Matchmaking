# Licence and provenance inventory

The original project remains owned by its authors; this packaging task grants no new licence or commercial rights to that code. No new open-source licensing choice is made on the team's behalf. The upstream submission instructions explicitly distinguish participation from commercial licensing.

The organizer starter licence and synthetic-data terms are retained at `research/starter/LICENSE`, `research/starter/DATA_LICENSE.md`, `runtime/starter/LICENSE` and `runtime/starter/DATA_LICENSE.md`. Source revision, data manifests and checksums are retained under `research/starter/` and `research/docs/SOURCE_PROVENANCE.json`. The public kit snapshot is used without changing its outcome definitions. No private organizer worlds or real-member records were added.

Python standard library is sufficient for the submitted serving path. The Docker base is `python:3.12.14-slim`; the validation tool resolves its registry digest and records the actual image identity on the executing machine. It has not been built here. Base-image components retain their own upstream licences.

Training/optional numeric dependencies are NumPy 2.3.5 and SciPy 1.17.0, both under BSD-style upstream terms and bundled third-party notices. They are not installed in the submitted serving image by this Dockerfile. Their pinned requirements remain in the full research package; the actual installed distribution notices used by the authoring environment are copied under `evidence/dependency_licences/`. Those notices include bundled-component terms where supplied. No model hub, paid API or remote inference service is required.

The new distribution tools are local packaging, report and validation utilities. The supplied official source, selected model, answer reservoir and prior evidence remain byte-identical to their recorded research/runtime inputs. AI-assisted review/implementation and its limitations are disclosed in the inherited research documentation; no claim of independent external certification is made.

Superseded previous-version archives and interruption snapshots were removed from this distribution. Retained flat collector inputs, observation lineage and test fixtures are documented in evidence/PACKAGE_CLEANUP.json. Executable research source, serving assets and experiment outcomes were not changed by this cleanup.
