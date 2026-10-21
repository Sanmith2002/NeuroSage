# Implementation Plan: Research-Only Synthetic Runtime Safety Assessment

**Branch**: `feature-08/Runtime-Safety-Assessment` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Approved synthetic-only internal simulation of a compatible Feature 007 selected-but-unevaluated policy.

## Summary

Compose the existing verified prediction, registry, frozen Feature 004 reference, Feature 005 estimator, Feature 006 calibrator, and Feature 007 policy into an internal synthetic-only simulation. Add a single-record bridge and an immutable private result while preserving all existing contracts. Never fit on the runtime query, expose a general patient assessment API, or imply independent evaluation.

## Technical Context

**Language/Version**: Python 3.11+ (per `pyproject.toml`)  
**Primary Dependencies**: Existing Safira modules; scikit-learn 1.7.1 remains pinned for the frozen estimator reconstruction. No new runtime dependency.  
**Storage**: None added; existing registry and trusted host integrations are injected.  
**Testing**: `uv run python -m pytest`; synthetic fixtures only.  
**Target Platform**: Existing Python library environments.  
**Project Type**: Python library; internal research/testing path only.  
**Performance Goals**: No user-facing latency target; synthetic correctness and fail-closed behavior are the acceptance measures.  
**Constraints**: Exact scope isolation; trusted admission before scoring; original-training-only reference reconstruction; frozen preprocessing, estimator, calibration, and cutoff; no protected final-test access; no new public per-patient API; no existing public contract changes.  
**Scale/Scope**: One synthetic prediction per call, independently processed per exact model/version/label/association; no batch pooling.

## Research Summary

The existing Feature 007 score bridge supplies reusable frozen Feature 005 and Feature 006 transformations but receives Feature 004 signal rows, not a standalone prediction. Its policy row builder is tied to a Feature 003 validation dataset. Feature 004 reference state is not portable, so a runtime test must reconstruct it from the independently verified original training evidence and compare the frozen state identity. A new private single-record bridge is therefore required.

The approved synthetic-only boundary excludes real patient data and any public or legacy `SafetyAssessment` output. The new immutable result records synthetic-test lifecycle and exact scope but omits the calibrated numeric score. Trusting real patient prediction, policy use, or production origin remains outside the feature.

## Constitution Check

| Principle | Plan alignment |
|---|---|
| I — Post-hoc reliability | The simulated output concerns correctness of an existing primary prediction; it is not a disease prediction, diagnosis, or treatment recommendation. |
| II — Classifier-scoped label isolation | Each call is bound to one exact model/version/label and prediction association. No model, label, or patient evidence is pooled. |
| III — Reuse existing contracts | Reuse `ModelAdapter`, `AdapterCapabilities`, registry, `PredictionRecord`, signal and artifact contracts where they fit. Add only private result and bridge types; no `SafetyAssessment` mutation or projection. |
| IV — Six safety dimensions | Use only the signal methods already declared by the exact Feature 004 protocol; introduce no signal dimension. |
| V — Frozen model-specific package | Apply artifacts only for the registered exact classifier/version/label. Synthetic simulation does not release a package or make it deployable. |
| VI — Independent evidence and protected test | Require original provenance and trusted verification; never read protected final-test evidence. |
| VII — Explicit signal availability | Preserve Feature 004 states and the frozen Feature 005 schema's missingness policy; never replace absent evidence with a reassuring value. |
| VIII–IX — Validated policy and safe abstention | No actual patient-label assessment occurs. `TRUST`/`CAUTION`/`DEFER` are emitted only inside synthetic fixtures, are marked `SYNTHETIC_TEST_ONLY`, and do not claim a validated policy or patient safety. Real assessment is unavailable. |
| X — Privacy and claim discipline | Keep identifiers, evidence, targets, scores, and verifier text out of results, logs, diagnostics, and exceptions; make no clinical claims. |
| XI — Automated verification | Add deterministic synthetic pytest coverage for success, trust failures, missingness, leakage, and compatibility. Tests do not stand in for empirical policy evaluation. |
| XII — Specification-driven change | Complete spec, plan, tasks, and cross-artifact analysis before implementation; preserve existing contracts. |
| XIII — Research prototype | Mark every result synthetic-only, unevaluated, non-clinical, and non-deployable. |

`SafetyContext` is not used as the runtime input because it carries raw patient data and does not establish Feature 002 admission or exact artifact provenance. `PredictionRecord` is authoritative for this simulation. `SafetyAssessment` is not used because its mutable, patient-associated serialization cannot enforce the synthetic/unevaluated lifecycle; the internal result is deliberately separate.

**Gate result**: Pass only for this approved synthetic-fixture simulation. Any expansion to real data, public output, or live runtime assessment requires a separate scope review and required independent policy evaluation/authorization.

## Design

1. **Admission**: Accept one synthetic `PredictionRecord` plus exact frozen package references. Run Feature 002 admission and registry compatibility checks; bind the prediction association and exact model/version/label to every estimator, calibrator, policy, and protocol. Verify artifact origin through the existing trusted host contract, including an exact origin check for the policy artifact. Reject shared trust failures atomically.
2. **Reference reconstruction**: Reuse Feature 007's original-training-only reconstruction approach. Independently admit original Feature 003 evidence and the approved Feature 004 protocol/manifest, reconstruct only the required state, and compare method/version/schema/preprocessing/scope and fitted digest to the frozen Feature 005/006/007 bindings. The runtime query is never included in fit inputs.
3. **Single-record signal derivation**: Reuse `SignalExtractor.extract_record` for configured stateless methods. Add private query-only application for frozen `knn_distance` and `domain_familiarity` state; derive the row and evidence lineage from the admitted record. Reject caller-supplied rows. Apply the frozen Feature 005 schema and estimator and the exact Feature 006 mapping using the private existing scoring functions.
4. **Policy application**: Verify the selected policy artifact and its protocol binding. Apply its one stored cutoff and stored inclusive/exclusive comparison without selection or modification. Keep the calibrated value ephemeral; map only to synthetic-test status and safe reason code.
5. **Result boundary**: Return an immutable internal result with exact source scope, non-reversible association fingerprint, artifact digests, status, and explicit synthetic/unevaluated lifecycle. Do not export it from the package root or map it into `SafetyAssessment`.
6. **Failure semantics**: Known missing/incompatible/unavailable inputs result in safe `DEFER` or atomic rejection as specified. Catch only documented domain failures. Unexpected programming exceptions remain distinguishable and are not disguised as ordinary readiness outcomes.

## Intended Project Structure

### Documentation

```text
specs/008-runtime-safety-assessment/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/runtime-python.md
├── quickstart.md
├── implementation-context.md
└── tasks.md
```

### Source and tests (planned only; not created in this design cycle)

```text
src/safira/runtime/
├── _records.py       # Internal immutable synthetic result
├── _exceptions.py    # Safe domain errors; unexpected exceptions remain visible
├── _verification.py  # Exact input and frozen-artifact admission
├── _signals.py       # Single-record Feature 004 query derivation
├── _scoring.py       # Frozen Feature 005/006 bridge
├── _policy.py        # Frozen Feature 007 cutoff comparison
├── _service.py       # Synthetic-only orchestration and policy mapping
└── __init__.py       # No public runtime assessment exports

tests/
├── runtime_fixtures.py
├── test_runtime_records.py
├── test_runtime_admission.py
├── test_runtime_signals.py
├── test_runtime_scoring.py
├── test_runtime_policy.py
├── test_runtime_privacy.py
├── test_runtime_boundaries.py
└── test_runtime_acceptance.py
```

**Structure Decision**: Add a private library subpackage and synthetic tests. Keep Features 001–007 source and public contracts untouched.

## Complexity Tracking

No constitution exception is requested. The private single-record bridge is the smallest design that avoids adapting a validation-dataset workflow into a public inference API.
