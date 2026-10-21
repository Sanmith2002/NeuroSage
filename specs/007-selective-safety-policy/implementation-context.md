# Feature 007 Implementation Context

Reusable reference for implementation sessions. Read this before exploring unrelated repository code.

## Approved scope and invariants

- Feature 007 is **Selective Safety Policy**. Feature 008 is provisional Runtime Assessment; independent final evaluation is a separate later feature.
- Per-scope identity is exact `(model_id, model_version, label_id)`; no pooling across labels, contributors, versions, or cohorts.
- Objective is maximum empirical patient-level TRUST coverage under a protocol-approved empirical selective-error ceiling; no statistical/clinical guarantee.
- Each patient contributes one deterministic, protocol-approved index assessment per exact scope. Eligibility and index choice are fixed before correctness outcomes are examined.
- One TRUST cutoff only. Valid below-cutoff predictions are CAUTION; invalid/unavailable/incompatible/not-ready inputs are DEFER. No public runtime application in Feature 007.
- The policy cohort is a new independently authorized Feature 003 build; its validation partition is reserved exclusively for selection. Feature 005 validation and Feature 006 calibration are spent. Protected final test is never accessed.
- Empty TRUST risk is undefined and cannot produce a successful policy. Constant scores cannot rank; only all-or-none selection may be assessed by the same empirical rule.
- The frozen result is selected-but-unevaluated, non-deployable and non-clinically-validated. Policy evidence is marked spent.
- No risk ceiling, minimum patient count, index assessment algorithm, or clinical threshold is hard-coded.

## Existing contracts to preserve

| Feature | Existing capability/constraint |
|---|---|
| 001 | Exact immutable model/version registration, label schema, adapter/classifier/preprocessing identity and prediction-class mapping. |
| 002 | `PredictionRecord` with independently verified Feature 002 source admission and exact assessment association. A constructed record/digest is not admission proof. |
| 003 | Verified binary correctness target, patient group, exact assessment/label binding, versioned manifest and patient-group partition. New independent dataset can reserve its own validation partition for policy selection. Protected rows are kept outside ordinary result. Cross-dataset patient-disjointness requires authoritative linkage/history evidence. |
| 004 | Six V1 dimensions; `SignalFeatureSet`, `SignalFeatureRecord`, `SignalRunManifest`, `FittedStateReference`. Reference state is trained from only Feature 003 training predictors. Current fitted state is not exported portably; reference metadata binds to original dataset/protocol/manifest. |
| 005 | `SafetyEstimatorArtifact` binds exact scope, registry identity, schema/preprocessing, original Feature 003/004 references, dependency and protocol. Feature 005 validation selection is spent. Public service trains; it does not infer. |
| 006 | `CalibratorArtifact` binds exact Feature 005 digest/family/version, schema/preprocessing, original Feature 003 calibration and Feature 004 references. Feature 006 calibration evidence is spent. Public service fits; it does not apply per-patient. Private `calibration.scores._reconstruct_scores` reconstructs base estimator scores only; it is not a public API and does not apply the calibrator mapping. |

## Private bridge design and exact limitation

There is no existing public API to score a distinct policy cohort. `SignalExtractor.build_feature_set` refits references on the dataset passed to it; `FittedStateReference` contains only safe identity/digests, not reusable vectors/vocabulary. Feature 005 and 006 expose no per-patient application API.

Feature 007 must implement a private adapter that:

1. Independently verifies original Feature 003 complete inventory and every embedded Feature 002 admission; isolates original `train` predictor evidence.
2. Reconstructs only Feature 004 reference state from those original training predictors and original approved signal configuration; checks state IDs/digests exactly against both frozen artifacts' original Feature 004 references.
3. Independently verifies new policy Feature 003 validation inventory, every embedded Feature 002 admission, exact ground truth, and cross-source patient disjointness from upstream/protected populations.
4. Generates each policy Feature 004 record itself from the admitted prediction and original approved method configuration, using existing stateless extraction semantics plus the reconstructed original reference state; aligns one row to one exact prediction. Never trust caller-constructed feature rows or fit on policy records.
5. Validates original Feature 005 and Feature 006 artifact origin/content/compatibility, then applies the exact frozen Feature 005 schema/preprocessing/base estimator and Feature 006 map in an ephemeral internal batch.
6. Emits only scope-level policy outcome/artifact; destroys row-level score/target/group values after aggregation.

Never change original artifact provenance to match the policy build; never call Feature 006 `calibrate` with policy evidence; never call the primary model; never use protected rows; never return individual q scores. If original evidence, trusted verification, exact state reconstruction, artifact origin, or independent dataset is unavailable, return `NOT_READY`.

## Proposed modules and dependency order

1. `records.py`, `exceptions.py`: immutable `PolicyScope`, protocol, evidence references, outcomes and artifact.
2. `verification.py`: explicit injected trusted verifier; full inventory, origin, patient history/linkage, Feature 001–006 scope and partition checks.
3. `references.py`: original Feature 004 training-only state recreation and exact digest comparison.
4. `signals.py`: derive each policy Feature 004 record from independently admitted Feature 002 predictions using the original method configuration and reconstructed references; enforce exact alignment.
5. `scoring.py`: exact allowlisted Feature 005 schema/preprocessing/estimator and Feature 006 mapping reconstruction; internal only.
6. `selection.py`: one index assessment per patient/scope, deterministic candidates, empirical risk/coverage, constant/empty behavior.
7. `artifacts.py`: immutable freeze, canonical digest, allowlisted serialization and safe validation.
8. `service.py`: atomic admission and per-scope workflow; public package exports omit scoring and patient-level operations.

Tests are written before each implementation group. Start with synthetic records and verifier doubles; add independent host-ledger tests, reference-digest reproduction, out-of-sample scoring numeric equivalence, patient-level cutoff calculations, no-refit leakage tests, whole-object serialization privacy inspection, and unchanged Features 001–006 regression.

## Trusted-host limitations

Injected verifier implementations and origin ledgers are host-controlled. The core can check their returned evidence is executed, exact-bound and consistent with submitted content, but cannot authenticate hostile code controlling the trusted Python host. There is no real production custodian or persistence integration. Test doubles prove software behavior only.
