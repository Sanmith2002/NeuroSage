# Implementation Plan: Automatic Model-Specific Safety Training

**Working branch**: `feature-05/Automatic-Safety-Training`

**Date**: 2026-10-21

**Specification**: [spec.md](spec.md)
**Status**: Planning complete; implementation not started

## Summary

Feature 005 consumes independently admitted Feature 003 correctness examples and their aligned Feature 004 predictor records. For each exact registered `(model_id, model_version, label_id)`, it fits a training-prevalence baseline and, when feasible, one fixed L2 logistic regression. It compares candidates once on the authorized validation partition using Brier score and freezes the selected **uncalibrated, non-deployable** research artifact. Scope failures remain independent.

## Technical Context

| Item | Decision |
|---|---|
| Language | Python 3.11+; current package uses `src/safira`. |
| Runtime dependency | Pin `scikit-learn==1.7.1` in `pyproject.toml` during implementation. Record exact installed NumPy, SciPy, joblib and threadpoolctl versions in each artifact. |
| Storage | No new database/service. Deeply immutable in-memory artifact and versioned allowlisted JSON-compatible export. Authorized storage and provenance remain host responsibilities. |
| Testing | pytest, synthetic test-first focused tests, Features 001–004 regression and full suite at integration. |
| Project type | Python research library; no REST/CLI deployment surface. |
| Performance | No approved latency or throughput target. |

## Constitution Check

| Principle | Design gate | Status |
|---|---|---|
| I–II | Post-hoc correctness, exact per-label classifier scope, patient grouping; no disease model training. | PASS |
| III | Consume Features 001–004; preserve `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, `SafetyAssessment` and registry contracts. | PASS |
| IV | Exactly six evidence families; no six-estimator requirement or mandatory numeric explanation score. | PASS |
| V–VI | Only estimator stage. Train fits, validation selects, calibration reserved, final test unavailable, later policy evidence distinct. | PASS |
| VII–VIII | Typed unavailable states, no fabricated zero or primary-model threshold, verified Feature 003 target only. | PASS |
| IX–XIII | Explicit non-success, privacy-safe artifacts, synthetic tests, SDD and prototype-only claims. | PASS |

Rechecked after Phase 1 design: no constitutional exception is needed.

## Existing Integration Surface

- Feature 001 fixes exact classifier, version, label, preprocessing and adapter compatibility. Shared labels or component versions do not imply shared estimator scope.
- Feature 002 `PredictionRecord` is constructible; independent admission evidence, not an object or caller digest, establishes source provenance.
- Feature 003 `DatasetBuildResult.development` contains train/validation/calibration `CorrectnessExample` rows with the verified binary `correctness_target` and restricted group references. Protected final-test data remain outside the ordinary result.
- Feature 004 `SignalFeatureSet` contains `training`, `validation`, `calibration` `SignalFeatureRecord` tuples, a dataset reference and `SignalRunManifest`. Each feature row has opaque `SignalRowKey`, exact `SignalSourceKey` and predictor `SignalResult`s. Feature 004 derives a row key from SHA-256 of `dataset_id + NUL + manifest_reference + NUL + complete prediction fingerprint`. Training reference signals are patient-group cross-fitted; validation signals use the frozen full-training reference. The feature-set dataclass itself is not trusted admission proof.

## Architecture and Data Flow

```text
Feature 001 registration ─────────┐
Feature 003 development result ───┼─> injected independent verifier + full local checks
Feature 004 SignalFeatureSet ──────┘                     │
                                                        v
                      exact source/row alignment and eligibility
                                                        │
                      per-scope frozen schema + train-only preprocessing
                                                        │
                      prevalence and fixed L2 logistic fit on train
                                                        │
                      one authorized validation Brier comparison
                                                        │
                      immutable uncalibrated research artifact
```

### Trusted admission before matrix construction

An explicit host-owned `TrainingInputVerifier` is injected into each trainer. It checks independently controlled Feature 003 dataset evidence, Feature 004 run/feature-set evidence and Feature 002 admission lineage for **every embedded prediction**. The library requires an executed typed result bound to actual complete content, exact dataset/protocol/version/manifest/builder, source inventory, signal method/configuration and fitted-reference identities, and full train/validation/calibration row inventory. It recomputes fingerprints and row keys, requires a bijection by role and unique rows, checks the exact Feature 001 registration, and verifies group disjointness. Caller-created checks, Booleans and matching digests alone establish no authority. Missing, incomplete, stale or mismatched independent evidence fails before target/predictor use. Host-owned provider injection is the trust root; core code cannot authenticate arbitrary malicious host-injected Python. No real clinical ledger is configured here.

The verifier may use opaque patient-group keys internally for eligibility/disjointness. Only ordered encoded predictors and Feature 003 `correctness_target` reach candidate fitting. Group keys, outcomes, association IDs, roles and verification evidence cannot enter predictors, preprocessing, candidate scoring or ordinary artifacts. Calibration is inventoried for admission completeness only; Feature 005 never builds its training matrix from it. Protected rows are outside the interface.

### Per-scope eligibility and frozen schema

One scope is formed per exact registered source. A versioned `TrainingProtocol` declares allowed Feature 004 `(dimension, method_id, method_version, semantics)`, required/optional features, non-value state policy, imputation/scaling/encoding, independent-patient and correctness-class adequacy, logistic settings and comparison prerequisites. No cross-label/version/contributor pooling. Missing approval is `NOT_READY`; approved but unmet support is `INSUFFICIENT_EVIDENCE`. No universal minima are invented.

Only approved finite `available` numeric signals, approved nominal domain `seen`/`unseen`, and allowlisted typed state indicators enter the ordered schema. `invalid`, `not_ready` and unverified evidence fail closed. `unsupported`, `missing`, `unavailable`, `insufficient_evidence` stay distinct; their non-value handling requires protocol approval. Universally unsupported dimensions are omitted with reasons. Required all-missing features cannot be constructed; optional all-missing and constant features follow a predeclared train-only omit/keep/fail rule. No validation-driven selection. Copied primary outputs, explanation provenance/applicability, method metadata and evidence references remain non-predictive.

### Preprocessing and candidates

Minimal V1 encoding: where approved, fit a training median for numeric non-value states and pair each computational fill with a separate typed state indicator. It is not a measured zero. Optional training-fitted mean/standard-deviation scaling uses unit scale for zero training variance, if protocol-approved. Nominal `seen`/`unseen` and allowlisted state categories use fixed one-hot order, not ordinal codes. If no observed training numeric value exists, apply the predeclared omit/fail rule; never invent a median. Freeze and reuse all learned preprocessing on validation.

The baseline probability is the exact scope's training-row correctness mean. Logistic uses scikit-learn 1.7.1 `LogisticRegression` with L2, `lbfgs`, `class_weight=None`, `fit_intercept=True`, `warm_start=False`, and protocol-fixed positive `C`, `tol`, and integer `max_iter`. Numeric values require research approval before validation is read; no search/retry. Single-class training cannot successfully fit logistic. Convergence warnings, numerical failures or non-finite output mark candidate failure. A one-class baseline may be described but cannot yield a successful artifact. Exact dependency versions are recorded.

### Selection and evidence lifecycle

Fit candidates and preprocessing on train only. Compute validation Brier `mean((p-y)^2)` for every valid predeclared candidate; lower wins and exact equality selects prevalence baseline. AUROC and average precision use correctness class 1 as positive and are reported only when meaningful/defined, with explicit undefined reasons and class support. Required feasibility is protocol-specific. A baseline winning a valid two-class comparison yields a `SELECTED_BASELINE` intermediate artifact; logistic yields `SELECTED_LOGISTIC`. Failed or undefined comparison is non-success. Validation scores are selection evidence, not unbiased final performance. Repeated visits make row-level descriptive scores correlated; no independent-patient CI is implied.

Do not run a second CV over already cross-fitted Feature 004 training features: a candidate holdout group's representation might already have influenced another row's reference score. Use existing Feature 003 validation for comparison. Cross-fitted training and frozen full-training-reference validation features may have different distributions. Never refit on validation. Mark validation spent; calibration remains reserved and a later policy requires distinct authorized evidence. Protected final test is inaccessible.

## Frozen Artifact and Failure Semantics

Accepted protocol, schema, preprocessing, comparison and artifact records are deeply immutable; `to_dict` returns detached, privacy-filtered data. The versioned artifact freezes the selected family and finite state (baseline prevalence or logistic class order/coefficient/intercept/dimension), exact Feature 001 identity, Feature 003 dataset/protocol/manifest, Feature 004 methods/run/fitted references, software/configuration, safe training metrics, validation selection metrics and evidence lifecycle. It is always `uncalibrated` and `non_deployable`. Ordinary artifacts/diagnostics exclude groups/rows, targets, raw predictors, restricted verification and protected data. Aggregate metrics/support are emitted only where the research protocol allows them; otherwise the artifact records a safe suppression reason.

Use a canonical, allowlisted JSON-compatible data export; validate shape, finiteness, digest, schema, exact compatibility and host-controlled origin on load. A digest detects change but does not authenticate source. Avoid untrusted `pickle`/`joblib` loading. Exportability is not durable persistence; no storage guarantee is claimed without an actual authorized custodian. Coefficients/statistics can themselves be sensitive and require controlled access.

Outcomes: `SELECTED_LOGISTIC`, `SELECTED_BASELINE`, `INSUFFICIENT_EVIDENCE`, `NOT_READY`, `UNAVAILABLE_REQUIRED_EVIDENCE`, `INVALID_INPUT`, `INCOMPATIBLE_INPUT`, `COMPARISON_UNDEFINED`. Candidate `FIT_FAILED`/`NONCONVERGED` is recorded safely; another candidate may be selected only under a predeclared required-candidate policy. A failed exact scope publishes no partial successful artifact. Shared admission failure invalidates all affected scopes.

## Project Structure

```text
specs/005-automatic-model-specific-safety-training/
├── spec.md
├── methodology-review.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/training-python.md
├── quickstart.md
└── implementation-context.md

src/safira/training/           # proposed; not created by this plan
├── __init__.py
├── records.py                # frozen records and artifact
├── verification.py           # trust and full alignment
├── features.py               # schema and frozen transform
├── candidates.py             # baseline, sklearn logistic, metrics
├── service.py                # per-scope orchestration
└── exceptions.py             # safe typed failures

tests/test_training_*.py      # proposed synthetic tests
```

These are cohesive ownership areas, not mandated public modules. [contracts/training-python.md](contracts/training-python.md) defines the proposed public surface.

## Verification and Dependencies

1. Test frozen records, nested immutability and serialization privacy.
2. Test forged/missing/stale admission, changed target/predictor, extra/missing/duplicate/wrong-role rows and group/source/reference mismatch before implementing verification.
3. Test all seven states, numeric/category encoding, train-only preprocessing, constant/all-missing columns and forbidden predictor fields.
4. Test baseline/logistic fit and failure, Brier/tie/undefined AUROC/AP, patient grouping, no refit, no calibration/test access and source isolation.
5. Test artifact compatibility, safe export/load, lifecycle labels, privacy and three-configurations end-to-end; run Features 001–004 and full pytest regression plus `git diff --check`.

Synthetic tests establish software boundaries, not scientific calibration, transport authentication or clinical effectiveness. A real trusted evidence ledger and approved protocol are external prerequisites.

| Requirements | Covered by |
|---|---|
| FR-001–007, FR-029; SC-001–004 | Existing integration, verifier, row alignment, per-scope data model and adversarial tests |
| FR-008–013 | Eligibility, schema, state/preprocessing contract and feasibility tests |
| FR-014–020 | Candidate policy, train/validation lifecycle and numerical tests |
| FR-021–028; SC-005–008 | Artifact, compatibility, reproducibility, failure and privacy tests |
| FR-030–033; SC-009 | Constitution boundary and Features 001–004 regressions |

## Planning Readiness

Mandatory versioned-protocol inputs before a non-synthetic run: exact group/class adequacy, feature allowlist and state policy, positive logistic `C`/`tol`/`max_iter`, optional feature rules, preprocessing and metric feasibility, and permitted aggregate reporting. Missing approval yields `NOT_READY`, never a scientific default. Host-owned verifier/ledger and authorized artifact custody are integration prerequisites, not hidden core guarantees. Ready for `$speckit-tasks` after review.
