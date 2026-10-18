# Feature 003 implementation checkpoints

Batch notes below are the historical implementation record. The post-audit remediation section at the end describes the current behavior and supersedes earlier limitation statements where they differ.

## Batch A — T001–T012

- Completed: package and synthetic fixtures, immutable supplemental records, explicit verifier result types and scope validation, exact registry label binding, verified outcome/independence joins, correctness from `predicted_class`, and a live-record acceptance path.
- Focused verification: `python -m pytest tests/test_dataset_records.py tests/test_dataset_verification.py tests/test_dataset_supervision.py tests/test_dataset_acceptance.py -q` — 7 passed. `git diff --check` passed.
- Self-review: inspected the new dataset modules and compared their trust boundaries with the implementation context and Python contract. Confirmed no edits to Feature 001/002 source modules and no adapter prediction calls in the build path. Corrected failures found in verifier type validation, tuple-key linkage freezing, manifest provenance access, and deterministic seed use.
- Decisions: Feature 002 does not expose a dedicated source namespace field, so the builder reads an explicitly supplied `source_namespace` from provenance details and otherwise uses the source-contract identifier, falling back to `unknown`. Dataset outputs carry only a manifest reference; the controlled manifest is not embedded in the ordinary result.
- Limitations for subsequent batches: remaining grouping, prior-history lifecycle, leakage/timing, protected handoff, reproducibility/privacy, adequacy, expanded multi-label/multi-contributor and precomputed acceptance coverage, full regression and quickstart update.
- Changed files: `src/safira/dataset/{__init__,builder,exceptions,partitioning,records,validation,verification}.py`; `tests/dataset_fixtures.py`; `tests/test_dataset_{records,verification,supervision,acceptance}.py`; `specs/003-patient-grouped-safety-dataset/tasks.md`.

## Batch B — T013–T020

- Completed: namespace-qualified alias resolution, verified linkage scope, duplicate/conflict handling, exact supplied assignments, one-pass seeded group allocation, prior-history exact binding, and protected-role movement checks.
- Focused verification: same dataset-focused command plus `tests/test_dataset_grouping.py` — 25 passed. `git diff --check` passed after the task-file update.
- Self-review: confirmed deterministic allocation hashes each group once from the approved seed; unsupported hard constraints fail closed before allocation. Verified history requires a typed check matching manifest content/version, origin/source, requested/declaration scope, completeness evidence and protected membership. Known protected membership must agree with the prior manifest and remain in `protected_test`.
- Limitation carried forward: this package does not interpret arbitrary site/time/strata constraints because no group attribute contract is defined in the approved inputs. It refuses such deterministic requests; the custodian must provide compatible supplied assignments or a separately approved constraint integration. The approved seed is never searched or replaced.
- Changed files: `src/safira/dataset/{builder,partitioning}.py`; `tests/test_dataset_grouping.py`; `specs/003-patient-grouped-safety-dataset/{tasks,implementation-checkpoints}.md`.

## Batch C — T021–T034

- Completed: trusted timing and transform lineage checks, prediction-time field separation, protected-test handoff isolation, canonical controlled manifest references and lineage, detached immutable values, protocol-scoped adequacy, end-to-end synthetic acceptance, compatibility assertions, quickstart and final regression.
- Final verification: Feature 003 focused tests **52 passed**; registry/collection/context/assessment/adapter compatibility regressions **401 passed**; full pytest suite **453 passed**; `git diff --check` passed.
- Self-review: confirmed the protected artifact is passed only to the supplied handoff, ordinary result fields/`repr`/serialization exclude protected rows and outcome content, adequacy reads development rows only, no inference/evaluation or estimator paths are called, verifier checks bind exact content/source/target or group/lineage scope and require authority/method/evidence references, and no Feature 001/002 source files were changed.
- Decisions and limitations: deterministic assignment hashes each group once using the exact configured seed and allocation order. Arbitrary hard site/time/strata constraints are returned as `INSUFFICIENT_EVIDENCE` because this repository has no approved group-attribute constraint contract. No trusted real-data integrations or storage service are configured; the returned manifest reference is a content digest, and callers/custodians remain responsible for controlled manifest persistence. Passing tests are synthetic software verification only.
- Changed files: `src/safira/dataset/*.py`; `tests/dataset_fixtures.py`; `tests/test_dataset_*.py`; `specs/003-patient-grouped-safety-dataset/{tasks,quickstart,implementation-checkpoints}.md`.

## Post-audit remediation — F1–F6

- Added exact-record Feature 002 admission checks through an explicitly injected trusted verifier; self-asserted provenance fields cannot admit records without a matching trusted check.
- Added an explicit custodian manifest handoff. The full immutable manifest is delivered only to that handoff; ordinary results expose only a digest reference and safe receipt.
- Applied per-label adequacy criteria independently to each exact model/version/label scope and added exact-key `adequacy_by_source` criteria.
- Enforced supported same-site assignment, timezone-qualified role windows, and allowed-strata membership for supplied and deterministic assignments. Unsupported constraints and missing group metadata report `NOT_READY`; infeasible supported constraints report `INSUFFICIENT_EVIDENCE`; no alternative seed is tried.
- Removed the shared `unknown` namespace fallback. Live namespaces must be explicitly supplied for the exact record or unambiguously identified by the verified linkage declaration.
- Made prior-history protected membership immutable and detached.
- Verification after remediation: focused Feature 003 tests **60 passed**; registry/collection/context/assessment/adapter regressions **401 passed**; full pytest suite **461 passed**; `git diff --check` passed. All added integration verifiers and records are synthetic test doubles; real external authority/storage remains unconfigured.
