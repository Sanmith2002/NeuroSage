# Implementation Plan: Selective Safety Policy

**Branch**: `feature-07/Selective-Safety-Policy-SDD` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification at `specs/007-selective-safety-policy/spec.md`.

## Summary

Feature 007 selects one empirical TRUST cutoff per exact model/version/label scope from a new, independently verified, patient-disjoint Feature 003 validation partition. Its empirical selective-risk ceiling and patient index-assessment rules are versioned protocol inputs, not clinical thresholds or guarantees. A narrowly scoped private scoring bridge verifies and reconstructs original Feature 004 references and the frozen Feature 005/006 estimator-calibrator chain, applies that chain to policy evidence without refitting, and returns only scope-level outcomes/artifacts. Missing trust evidence or exact state reproduction yields `NOT_READY`. Feature 007 freezes a selected-but-unevaluated, non-deployable artifact; independent policy evaluation and runtime assessment remain later work.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing Safira package and dependencies; scikit-learn 1.7.1 remains the approved Feature 005 dependency. No additional runtime dependency is planned.
**Storage**: In-memory immutable protocol/outcome/artifact records and allowlisted serialization; no new database or durable-storage service. A caller/custodian may persist artifacts under separately controlled procedures; the core makes no persistence guarantee.
**Testing**: pytest, synthetic records only, focused Feature 007 tests plus unchanged Features 001–006 regression suite.
**Target Platform**: Existing Python package targets.
**Project Type**: Python research library.
**Performance Goals**: No unapproved latency or throughput target. Cutoff evaluation is deterministic and scoped; candidate enumeration should reuse sorted scores rather than repeatedly sort.
**Constraints**: No protected final-test access; no use of spent Feature 005 validation or Feature 006 calibration data; no changes to Features 001–006 public contracts; no patient-level score API; no refitting on policy-selection records; no new thresholds, minima, or empirical guarantees.
**Scale/Scope**: One policy-selection cohort, exact-scope outcomes for supported registered labels, independent patient index assessments, synthetic verification. No fixed contributor count, disease, classifier architecture, or label name.

## Constitution Check

| Principle | Plan compliance |
|---|---|
| I. Post-hoc reliability, not disease prediction | Threshold ranks the frozen correctness estimator's output for primary-prediction correctness. It is not a disease score or diagnosis. |
| II. Classifier-scoped labels and patient isolation | Each `(model_id, model_version, label_id)` is independent; one protocol-selected index assessment per patient/scope; no cross-scope pooling. |
| III. Preserve adapters and assessments | No modifications to `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment`; no runtime assessment. |
| IV. Exactly six dimensions | Feature 007 consumes approved Feature 004 outputs; it defines no new signal dimension. |
| V. Model-specific safety sequence | Selects only a policy bound to one estimator/calibrator chain; it does not train, calibrate, evaluate, or deploy a complete package. |
| VI. Independent data and untouched test | New independent patient-disjoint policy evidence only; prior development/calibration and protected final test excluded. Policy selection is separate from later independent evaluation. |
| VII. Explicit availability | Invalid/unavailable/incompatible/not-ready inputs defer or fail safely; no fabricated score or cutoff. |
| VIII. Evidence-derived operating point | Empirical risk/coverage are calculated from verified outcomes and a preapproved protocol, not arbitrary constants. No guarantee is claimed. |
| IX. Safe abstention and readiness | Feature 007 outputs only a selected-but-unevaluated artifact and readiness results; it exposes no runtime status application. |
| X. Privacy and claims | Identifiers, outcomes, row scores, restricted data and verifier payloads excluded from ordinary results. No clinical/deployment claim. |
| XI. Tests and reproducibility | Synthetic positive/negative/leakage/privacy tests; deterministic inputs/protocol; existing regression suite. |
| XII. Specification-driven change | This plan and dependency-ordered tasks precede implementation; upstream contracts remain unchanged. |
| XIII. Research prototype | Explicitly non-clinical, non-deployable, not independently evaluated. |

**Gate result**: Pass, subject to the trusted-host evidence providers and original approved training inputs existing at execution time. If they do not, Feature 007 must return `NOT_READY`; no trust claim or inferred data separation is permitted.

## Architecture

### Trust and evidence flow

1. An explicitly injected trusted-host verifier independently checks the new policy Feature 003 dataset, all embedded Feature 002 admissions, verified correctness targets, index-assessment selection, cross-source patient linkage/history, artifact origins, and exact inventory.
2. The verifier checks the frozen Feature 005 artifact against the exact Feature 001 registration and original Feature 003/004 references, and the Feature 006 calibrator against the exact Feature 005 digest, Feature 006 provenance, and origin evidence. The original artifact bindings stay unchanged.
3. Feature 007 reconstructs only the exact Feature 004 fitted state referenced by the artifacts, using verified original Feature 003 training predictor evidence and the original method protocol. It checks each deterministic state digest against the recorded fitted-state references before use. It never fits on the new policy dataset.
4. Feature 007 derives each policy signal row from the already admitted Feature 002 prediction using the original approved Feature 004 method configuration: it reuses the existing record-level stateless extraction semantics and applies only the exact reconstructed original reference states for reference-based dimensions. It does not accept caller-constructed signal rows as trusted input. It aligns each generated row to exactly one policy prediction, applies the exact ordered Feature 005 schema/preprocessing/estimator, and then the validated Feature 006 mapping. The primary classifier is not called. Per-patient calibrated scores exist only in a short-lived internal selection batch.
5. For each exact scope, selection evaluates protocol-permitted deterministic cutoffs and computes patient-level empirical risk and coverage. It emits one immutable policy artifact per successful exact scope or a typed non-success. No row-level scores or outcomes are returned.

The original Feature 005/006 training/calibration provenance and the new policy-selection provenance are independent artifact fields. A new policy manifest is never substituted for the original model-training or calibrator manifest.

### Private scoring bridge limitation and safe boundary

Existing public contracts do not provide the complete out-of-sample operation:

- Feature 004 emits `FittedStateReference` metadata bound to its original Feature 003 dataset/protocol/manifest, but does not export the fitted vector/vocabulary state or provide a general ordinary-data apply API. Its current `SignalExtractor.build_feature_set` refits references from the supplied dataset's training partition.
- Feature 005 exposes training and artifact validation, not estimator inference.
- Feature 006 exposes calibrator fitting and artifact validation, not calibrated per-patient application. Its private score helper reconstructs the base estimator score, not the calibrated output, and its calibration bundle verification is bound to the original calibration dataset.

Therefore the new cohort cannot safely be scored by passing it through the existing Feature 004–006 public workflows. Feature 007 must own a narrow private adapter: re-derive Feature 004 reference state from original verified training evidence; require exact digest equality with the frozen references; derive policy signal rows from admitted predictions using the original approved Feature 004 method configuration, combining its record-level stateless extraction with application of only the reconstructed original reference states; require exact prediction/row alignment; encode/transform with the existing frozen Feature 005 schema and preprocessing; reconstruct the exact frozen estimator; apply the exact frozen Feature 006 mapping. Caller-constructed policy signal rows are never accepted as trusted evidence. No upstream public interface is changed or bypassed: each existing artifact's content, origin, identity, and original provenance is validated, while Feature 007 separately validates the new policy dataset. The new adapter returns only the ephemeral internal selection batch. Any unavailable original data, unsupported artifact version, digest mismatch, missing verifier, or unprovable disjointness yields `NOT_READY` or incompatibility before cutoff selection.

This is a trust-host integration point, not a cryptographic guarantee. The core cannot authenticate arbitrary malicious code controlling the trusted Python host. No production origin ledger, independent custodian, or policy-selection evidence is configured in the repository today.

### Empirical cutoff calculation

For one protocol-eligible index assessment per patient and exact scope, with private calibrated correctness-estimator score `q_i`, verified correctness target `y_i ∈ {0,1}`, and a protocol-declared selection predicate `S_t(q_i)`, calculate:

`R_emp(t) = count(i: S_t(q_i) and y_i = 0) / count(i: S_t(q_i))`, defined only for nonempty selected sets; and `C_emp(t) = count(i: S_t(q_i)) / count(i: eligible)`, defined only for a nonempty eligible scope.

The versioned protocol fixes the population/index rule, candidate-generation rule, equality semantics, ties, risk ceiling, and support criteria before outcomes are examined. The algorithm evaluates only those candidates, rejects empty TRUST sets as successful outcomes, then chooses maximum feasible coverage. Tied selected-set/coverage outcomes use the deterministic rule frozen in the protocol. These are empirical selection-cohort values; they are not statistical bounds or independent evaluation estimates.

### Public boundary

The public workflow is cohort-level policy selection/freeze with explicit verifier injection. It provides status, reason codes, safe aggregate selection metrics when protocol disclosure permits, and an immutable selected-but-unevaluated artifact. It has no `predict`, `apply`, calibrated score, patient status, `SafetyContext`, `SafetyAssessment`, or runtime method. Selected artifacts remain non-deployable until a later independent evaluation and separately scoped runtime work.

## Project Structure

### Documentation (this feature)

```text
specs/007-selective-safety-policy/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-context.md
├── contracts/policy-python.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/safira/policy/
├── __init__.py          # narrow public protocol/result/service/artifact exports
├── records.py           # immutable protocol, scope, provenance, outcome, artifact
├── verification.py      # injected host boundary and exact admission orchestration
├── references.py        # private original Feature 004 state reconstruction and digest checks
├── signals.py           # private per-prediction Feature 004 row generation/alignment
├── scoring.py           # private frozen Feature 005/006 score reconstruction
├── selection.py         # deterministic empirical cutoff selection
├── artifacts.py         # allowlisted canonical policy artifact export/validation
├── service.py           # atomic verification, selection and artifact lifecycle
└── exceptions.py        # stable privacy-safe failures

tests/
├── policy_fixtures.py
├── test_policy_*.py
└── test_policy_acceptance.py
```

**Structure Decision**: Add one cohesive `safira.policy` research package with clear private signal-generation/scoring/reconstruction helpers. Reuse Features 001–006 records and approved mathematical method semantics; do not modify or add exports to upstream packages.

## Research Decisions

All research-critical choices were approved before this plan. See [research.md](research.md) for candidate-method review, primary references, and limitations. Implementation must not supply protocol-owned numerical values.

## Design Artifacts

- [Data model](data-model.md)
- [Python contract](contracts/policy-python.md)
- [Quickstart and verification guide](quickstart.md)
- [Reusable implementation context](implementation-context.md)

## Complexity Tracking

No constitutional deviation is requested. The private scoring bridge is the minimum new component needed because existing public APIs deliberately have no estimator/calibrator inference path and Feature 004 does not expose portable fitted reference state. It is isolated within Feature 007, guarded by exact upstream verification, and may return `NOT_READY`; it does not weaken upstream constraints.
