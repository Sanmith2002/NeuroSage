# Feature 008 Data Model

All entities below are internal to the synthetic research/testing path. They are not persisted, exported from the package root, or accepted as substitutes for trusted host checks.

## SyntheticRuntimeRequest

One synthetic query and the frozen provenance required to evaluate it.

| Field | Type / constraint | Purpose |
|---|---|---|
| `prediction` | Exact `PredictionRecord` | Synthetic primary prediction and source evidence. |
| `scope` | Exact Feature 007 `PolicyScope` | Model/version/label plus registered classifier and adapter identity. Must equal prediction source and all three artifacts. |
| `original_dataset` | Verified `DatasetBuildResult` | Original Feature 003 evidence used only for trusted inventory verification and original training predictors. No protected partition. |
| `original_reference` | Exact `Feature003DatasetReference` | Dataset, protocol, manifest and builder identity for the frozen Feature 004 state. |
| `original_signal_protocol` | Exact `SignalProtocol` | Approved method/version/schema/preprocessing settings and exact sources. |
| `original_signal_set` | Exact `SignalFeatureSet` | Original Feature 004 manifest and fitted-state references bound by Feature 005/006. The runtime service reads only metadata needed to compare frozen bindings. |
| `estimator` | Exact `SafetyEstimatorArtifact` | Frozen Feature 005 estimator for this scope. |
| `calibrator` | Exact `CalibratorArtifact` | Frozen Feature 006 mapping bound to this estimator and scope. |
| `policy_protocol` | Exact `PolicySelectionProtocol` | Approved Feature 007 protocol whose digest is frozen in the policy artifact. |
| `policy` | Exact `SelectivePolicyArtifact` | Selected-but-unevaluated cutoff artifact for this scope and estimator/calibrator pair. |

The runtime query contains no correctness target, and no protected-test partition is admitted. The original `DatasetBuildResult` may retain its existing supervised provenance, but runtime admission/reference reconstruction MUST NOT read or derive correctness targets. Assessment association is taken from the admitted prediction, not a second caller-supplied identifier.

## RuntimeVerifier (trusted-host interface)

An injected host object that executes and returns exact typed verification results for prediction admission, original dataset admission, protocol approval, and artifact origin. Each response must bind to the exact submitted fingerprint/digest, scope, version, and artifact type. Feature 008 does not create or accept self-asserted receipts. The synthetic test verifier is test-only and is not evidence for real data.

## FrozenRuntimeBundle

An ephemeral, verified composition of the exact registry identity, original Feature 004 method configuration and reconstructed reference state, Feature 005 estimator transform, Feature 006 mapping, and Feature 007 cutoff semantics. It is constructed only after complete shared admission and discarded after the one synthetic query.

## InternalResearchAssessmentResult

| Field | Type / constraint | Purpose |
|---|---|---|
| `scope` | Exact `(model_id, model_version, label_id)` tuple | Prevent scope pooling or artifact substitution. |
| `association_fingerprint` | Non-reversible digest | Bind to the exact admitted synthetic assessment without retaining identifiers. |
| `status` | `TRUST`, `CAUTION`, or `DEFER` | Simulated status for a valid synthetic fixture or safe readiness failure. |
| `reason_code` | Allowlisted non-sensitive token | Explain readiness/status without verifier text or input values. |
| `estimator_digest` | SHA-256 | Frozen provenance. |
| `calibrator_digest` | SHA-256 | Frozen provenance. |
| `policy_digest` | SHA-256 | Frozen policy provenance. |
| `execution_mode` | Exactly `SYNTHETIC_TEST_ONLY` | Prevent confusion with real runtime assessment. |
| `policy_status` | Exactly `SELECTED_UNEVALUATED` | Preserve Feature 007 lifecycle. |
| `independent_evaluation_complete` | Exactly `False` | No independent evaluation claim. |
| `protected_test_accessed` | Exactly `False` | Preserve test boundary. |
| `deployable` | Exactly `False` | No deployment authorization. |
| `clinical_validity_established` | Exactly `False` | No clinical claim. |

No raw identifiers, calibrated scores, evidence payloads, targets, signal rows, patient data, or verifier responses are fields of the result. Non-success outcomes contain no fabricated score or partial frozen bundle.

## State Flow

`SYNTHETIC_INPUT` → `SHARED_ADMISSION_VERIFIED` → `FROZEN_BUNDLE_COMPATIBLE` → `SYNTHETIC_RESULT`.

Any missing, invalid, forged, or mismatched shared check stops before scoring with no result. A valid but unavailable optional signal follows only its exact frozen Feature 005 missingness behavior. A fully admitted query with a missing/unavailable/invalid/incompatible required runtime measurement produces `DEFER` with an allowlisted reason and no score. The result is never promoted to independently evaluated, clinically valid, or deployable.
