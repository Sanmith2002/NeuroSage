# Implementation Plan: Safety Signal Extraction and Feature Engineering

**Branch**: `004-safety-signal-extraction` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

## Summary

Add an in-process `safira.signals` package that turns validated Feature 002 predictions/evidence into six-dimension, source-qualified signal results, and aligns predictor-only feature rows with Feature 003 development examples. Stateless evidence coverage, binary entropy, modality JSD and explanation metadata are separated from training-reference kNN distance and domain-category familiarity. Reference-based training rows use deterministic patient-grouped cross-fitting; final reference state uses only the approved Feature 003 training partition. Protected-test application is an external custodian-controlled apply-only boundary. No safety estimator, reliability calibration, policy, runtime assessment or clinical claim is added.

## Technical Context

**Language/Version**: Python 3.11+ (repository requirement).  
**Primary Dependencies**: Python standard library only for V1 arithmetic, immutable records and protocols. Do not add NumPy/SciPy/scikit-learn solely for the initial methods.  
**Storage**: None in the Feature 004 core. Fitted values and manifests are immutable in-process objects with detached serialization; persistence/restricted storage belongs to a separately authorized host/custodian integration.  
**Testing**: pytest, synthetic Feature 001/002/003 values, no patient data.  
**Target Platform**: Existing Python library.  
**Project Type**: In-process library package.  
**Performance Goals**: No unsupported latency target. Reference kNN uses an explicit linear scan with O(N·d) distance work per query; suitability must be reported by the research protocol for its cohort size.  
**Constraints**: Preserve all Feature 001–003 and adapter/context/assessment contracts. No universal minimum, threshold, fit on held-out partitions, alternate-seed search or unapproved feature transformation. Exact source identity and evidence provenance remain attached to every result.  
**Scale/Scope**: Research prototype; standalone binary, multi-label and arbitrary independent component contributors; per-contributor `(model_id, model_version, label_id)` scope.

## Constitution Check

| Principle | Plan alignment |
|---|---|
| I. Post-hoc reliability, not disease prediction | Extractors describe evidence; they do not predict disease, score safety or assess patients. |
| II. Classifier-scoped labels and patient isolation | Keep contributors/labels independent; cross-fitting groups every patient record together. |
| III. Preserve existing contracts | Consume existing registry, collection, dataset and adapter values; do not change `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment`. |
| IV. Exactly six dimensions | Exactly the six specified dimensions; a dimension may have a structured result/state rather than a numeric value. |
| V. Safety packages | No estimator training or safety-package creation. |
| VI. Independent data and untouched test | Reference fits use Feature 003 training predictor evidence only; validation/calibration are apply-only; protected test is externally controlled apply-only. |
| VII. Explicit availability | Preserve Feature 002 states and emit a distinct Feature 004 signal state; never substitute zero. |
| VIII. Evidence-derived targets | Correctness/outcomes remain excluded from all signal values and fit inputs. |
| IX. Readiness and abstention | Only method readiness is reported; no TRUST/CAUTION/DEFER or clinical readiness claim. |
| X. Privacy | No patient-level input/ID in ordinary logs, errors, run manifests or feature values; protected values remain custodian-side. |
| XI. Tests and reproducibility | Synthetic pytest coverage, deterministic configuration and manifests; empirical validation is reported separately. |
| XII. Specification-driven changes | Implementation follows this plan and dependency-ordered tasks; no existing functionality rewrite. |
| XIII. Research prototype | Documentation and APIs make no clinical-validation claim. |

**Gate result**: PASS. No constitutional exception is needed.

## Architecture

### Data flow

1. Accept one `PredictionRecord` or a Feature 003 development dataset bundle. Require a ready Feature 003 build for reference fitting and an explicit dataset identity/provenance check through the configured Feature 004 dataset-verification boundary. Validate Feature 002 source key, evidence state and interpretation against exact Feature 001 metadata from `ModelRegistry.get_metadata(model_id, model_version)`. When consuming embedded records, require independent Feature 002 admission verification for every exact row before any signal or cohort/reference operation uses it.
2. Calculate stateless signals from the accepted record only: evidence coverage/validity, Bernoulli entropy, pairwise modality JSD, and explanation applicability metadata.
3. For reference fitting, use only `DatasetBuildResult.development.train` predictor evidence after the complete dataset and embedded-row admission check succeeds. Assign folds from unique Feature 003 patient-group references using the versioned cross-fit configuration and deterministic SHA-256 group hashing with the single declared seed. All visits, labels and contributors for a group share one fold. Fit each fold reference without that fold; score only its held-in training rows. Do not use a fallback seed. If valid compatible evidence cannot satisfy a protocol-required fold/reference support criterion, return `insufficient_evidence`; if required approval, trusted verification, provenance, or compatible state is absent or unestablished, return `not_ready`.
4. After cross-fit training rows are generated, fit the final immutable reference state on the full approved training predictor set for future permitted transforms. It is scoped to the exact dataset/protocol/manifest reference, model/version/label, preprocessing identity, evidence schema, method version and parameters.
5. Transform validation/calibration development rows only with the frozen final state. Do not fit, update, select parameters or derive adequacy from those rows.
6. Protected-test records are never passed to ordinary APIs. If explicitly authorized later, an injected custodian integration performs an apply-only operation for a frozen compatible state and exact Feature 003 scope, retaining protected transformed values in a restricted artifact; ordinary Safira sees only a privacy-safe receipt/status.

### Proposed package layout

```text
src/safira/signals/
├── __init__.py       # small public API
├── base.py           # protocols, dimensions and state constants
├── records.py        # immutable configs, results, references and manifests
├── validation.py     # exact identity, evidence, partition and leakage checks
├── stateless.py      # coverage, entropy, modality JSD, explanation metadata
├── reference.py      # deterministic folds, kNN/domain fit, cross-fit and apply
├── service.py        # orchestration for records and Feature 003 development rows
└── exceptions.py     # privacy-safe typed signal errors
```

The custodian apply-only boundary is a structural protocol in `base.py`/`service.py`; the Feature 004 core does not implement protected storage or receive protected values. This is a small number of cohesive modules and introduces no database, service or global mutable state.

### Signal method contracts

| Dimension | V1 operation | State and behavior |
|---|---|---|
| Data sufficiency | Per-record vector of method-required evidence coverage/validity states. Separate cohort support summary counts unique patient groups, and correctness classes only where approved protocol requires them, for exact contributor scope. | Evidence profile is stateless. Cohort summary is restricted metadata and never a predictor feature. No generic score or universal minimum. |
| Distribution conformity/OOD | Raw k-th-nearest distance in a declared compatible representation, metric and preprocessing space. | Reference-fitted on Feature 003 train; cross-fit training values. Metric and `k` are protocol-specified. No threshold, probability conversion or class-specific inference. |
| Prediction uncertainty | `H(p)=-p log(p)-(1-p)log(1-p)` for registered binary probability; optional repeated-output variance over validated same-input draws. | Entropy is stateless. Repeated variation is optional, descriptive and provenance-dependent; no epistemic/aleatoric decomposition. |
| Modality agreement | Pairwise Bernoulli JSD for two or more comparable modality-specific probability outputs for the same contributor/label/assessment. | Stateless. Log base/pair or aggregation rule are explicit protocol values. Separate classifiers are never compared or fused. |
| Domain familiarity | `seen`/`unseen` category membership in an approved reference vocabulary; category identifiers/support counts remain restricted. | Vocabulary fitted to Feature 003 train and cross-fitted for training rows. Protocol defines category semantics and privacy allowance. Not cohort shift/OOD. |
| Explanation reliability | Preserve method/target/output-space/calibration metadata and applicability; no numeric reliability score. | Stateless metadata. Perturbation fidelity/sensitivity/stability and randomization audits are deferred. |

All method parameters and adequacy criteria are versioned and approved by the research owner before extraction. Synthetic fixtures verify calculations and contract enforcement, not empirical validity.

### Feature 003 integration and trust boundary

`DatasetBuildResult` is frozen by convention and exposes development train/validation/calibration values, a manifest reference and safe receipt/summary fields; it does not carry the full controlled manifest or protected rows. Since a caller can construct values of public dataclasses, the Feature 004 boundary requires an explicitly injected `DatasetInputVerifier` to execute a source-specific check against independently controlled build evidence. Its immutable check binds the exact detached development input fingerprint, dataset/protocol/manifest references, readiness and partition memberships, plus every embedded prediction's independently verified Feature 002 admission. The row inventory binds each canonical prediction/evidence content fingerprint to its exact source key, association/occurrence, model/version/label, Feature 002 admission lineage, Feature 003 dataset and authorized development partition. An aggregate attestation is acceptable only when independent controlled evidence covers the complete exact row inventory and every row's admission lineage; otherwise the integration verifies each row individually. A bool, `ready` status, caller digest, outer dataset acceptance or `manifest_reference` alone is insufficient. Missing, changed, substituted, stale or conflicting row evidence fails closed before cohort support, signal values, fitting or feature-set publication. Feature 004 validates exact check scope but does not claim universal proof or durable persistence.

Feature 003 alignment uses a run-scoped opaque `SignalRowKey` separate from predictor values. The key is mapped to a source-qualified Feature 002 record and exact Feature 003 example while building rows; patient, assessment, occurrence, group, partition role, target, outcome and correctness target never enter `SignalFeatureRecord.features`. Partition role gates allowed operations only. Ordinary results include development rows and safe metadata; no full manifest, protected row or protected signal value is included.

### Failure behavior

Signal-level states have the Feature 004 meanings in the specification: unsupported, missing, unavailable, invalid, insufficient evidence and not ready. Feature 002 evidence state and provenance remain unchanged in lineage. Invalid identity, scope conflict, malformed numeric values, non-finite vectors, incompatible shapes/preprocessing and prohibited partition inputs produce typed privacy-safe failure or non-value states. A failure in one optional signal does not remove valid independent signals. Non-finite entropy/JSD/distance results are invalid; a valid but inadequate reference is insufficient evidence; a missing approved reference or verifier is not ready.

## Requirement traceability

| Feature areas | Planned components |
|---|---|
| FR-001–FR-010, SC-001–SC-003 | `validation.py`, `stateless.py`, `service.py`; exact source identity, row-level Feature 002 admission, configuration variants, states and non-aggregation tests. |
| FR-011–FR-016 | `stateless.py`, `reference.py`; six method-specific calculation/metadata and availability tests. |
| FR-017–FR-020, SC-004–SC-006, SC-010 | `reference.py`; verified-row-only training fit, deterministic grouped folds, self-exclusion, exact compatibility and reproducibility tests. |
| FR-021, SC-008, SC-011 | injected custodian apply-only protocol; fake-custodian boundary tests, ordinary-surface inspection. |
| FR-022–FR-027, SC-004, SC-007–SC-008 | `records.py`, `validation.py`, `service.py`; leakage, immutability, safe errors, provenance and contract regressions. |
| FR-028–FR-029, SC-009 | public API boundary and acceptance tests; assert no estimator, calibration, policy or assessment behavior. |

## Test strategy

- Add tests first under `tests/test_signals_*.py`, using existing `registered_collection`, `CollectionAssociation`, `PredictionRecord`, `EvidenceItem`, `DatasetBuildResult`, and synthetic fixture patterns.
- Test formula fixtures for entropy (including `p=0`/`1`), JSD (equal/opposite Bernoulli distributions), Euclidean kNN ordering, domain membership and evidence-state coverage. Use tolerances only for floating-point equality; no clinical thresholds.
- Test standalone binary, multi-label and independently composed contributors with overlapping labels and exact version checks.
- Test signal states against each Feature 002 evidence state and malformed, non-finite, unsupported and semantically incompatible values.
- Test deterministic patient-group folds, group-wide exclusion (including other labels and visits), protocol seed use once, no alternate seed search, infeasible fold/reference outcomes, and final reference fitted exclusively from training rows.
- Mutate validation/calibration/outcome/correctness/protected input while holding allowed training predictor evidence and verified grouping fixed; fitted state and development feature values must remain unchanged. Separately change verified patient grouping and assert fold assignments or cross-fitted scores may change, while every scored group's full records remain excluded from its reference, no prohibited information enters predictor features, and no patient identifier is emitted.
- Inspect complete result objects and every serializer/error/log surface for protected content, supervision, identifiers and raw evidence leakage; verify deep immutability.
- Test dataset verifier missing, false, wrong-content, wrong-dataset/version/protocol/manifest, wrong partition, stale and incomplete results. For embedded predictions, test forged records, changed value/evidence/provenance, wrong source/association, missing/stale row-admission lineage, incomplete aggregate inventory, and a verified exact-row positive case. Test custodian handoff receives only frozen state/scope references, never protected rows, and ordinary callers receive no transformed values.
- Test SC-004's independent invariants: outcome/correctness changes do not alter predictor features; validation/calibration/protected mutations do not alter training reference state; verified grouping changes may alter fold assignments/cross-fit values but cannot allow self-inclusion or identifier leakage; renaming only opaque group references leaves the final full-training reference unchanged.
- Run focused Feature 004 tests, Feature 001–003 regressions, then full `pytest`. Tests establish software behavior only; empirical validation requires a separate protocol and independent data.

## Dependencies and risks

**Dependencies**: completed exact Feature 001 metadata and `ModelRegistry.get_metadata`; accepted Feature 002 `PredictionRecord`/five-state evidence; Feature 003 ready development `DatasetBuildResult`, patient-group assignments, source/target verification lineage and exact manifest references; an application-provided trusted `DatasetInputVerifier` for production evidence; an authorized custodian integration for any protected transformation.

**Unresolved implementation risks**:

- No real Feature 003 verifier/custodian integrations are configured. Synthetic trust ledgers cannot validate deployment authority or persistence.
- Feature 002 optional evidence semantics vary by source; exact schema/interpretation compatibility must be validated before formulas run.
- Representation scaling and metric, `k`, cross-fit fold count/seed, JSD aggregation/log base, domain-category semantics, and adequacy criteria require study-specific protocol approval; no default should be silently selected.
- Hash grouping can be imbalanced and leave a fold with too few reference groups. It fails safely and does not search seeds; the protocol must determine whether the resulting research scope is feasible.
- A small cohort may make grouped cross-fitting infeasible. The correct output is `insufficient_evidence`, not a patient split or an in-sample score.
- Opaque row keys and domain vocabularies remain restricted controls; normal logs, results and manifests must not reveal their values.
- Synthetic and unit tests cannot establish scientific or clinical utility.

## Complexity Tracking

No constitution violations or new infrastructure are planned. An injected `DatasetInputVerifier` and custodian apply-only protocol are boundary contracts only; real verification/storage remains host-owned, consistent with Feature 003's existing pattern.
