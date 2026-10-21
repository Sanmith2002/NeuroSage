# Feature 007 Data Model

Feature 007 records evidence references and policy-level outcomes. Patient-level scores and outcomes are ephemeral internal values and are not ordinary entities or serialized records.

## Existing authoritative inputs

| Input | Source | Feature 007 use | Binding rule |
|---|---|---|---|
| `ModelMetadata` / `ModelRegistration` | Feature 001 registry | Exact classifier, version, label, adapter, classifier fingerprint, preprocessing identity, prediction-to-class mapping | Resolve each `TrainingScope.source_key`; no cross-version or cross-label reuse. |
| `PredictionRecord` | Feature 002 | Primary score, predicted class, evidence and source-qualified provenance | Independently verify each record's executed Feature 002 admission, content and assessment association. |
| `DatasetBuildResult`, `CorrectnessExample`, `DatasetManifest` | Feature 003 | Ground truth, correctness target, patient group, partition role and dataset/manifest references | Trusted full-inventory verification; validate target and prediction binding; ordinary policy input uses only the new build's validation partition. |
| `SignalFeatureSet`, `SignalFeatureRecord`, `FittedStateReference` | Feature 004 | Approved V1 measurements and original fitted-reference provenance | Match exact row, scope, source, method/version/parameters, preprocessing, original reference digest and original manifest. |
| `SafetyEstimatorArtifact` | Feature 005 | Frozen exact-scope estimator, ordered schema, preprocessing, coefficients/baseline, origin and original training references | Validate canonical artifact, origin, exact scope and original compatibility. Keep original references unchanged. |
| `CalibratorArtifact` | Feature 006 | Frozen exact-scope mapping and its original calibration/base-artifact provenance | Validate content, origin, exact base digest/family/version, schema/preprocessing, scope and original dataset/signal references. No call to calibration fitting. |

## Feature 007 entities

### `PolicyScope`

One exact `(model_id, model_version, label_id)`; must match the Feature 001 registration, Feature 005 estimator scope, Feature 006 calibrator scope, Feature 004 source key and policy dataset prediction inventory.

### `PolicySelectionProtocol`

An immutable versioned protocol with:

- exact allowed scopes and model/adapter compatibility references;
- selection purpose and a new Feature 003 dataset whose validation partition is reserved for policy selection;
- patient-level eligibility and deterministic one-index-assessment-per-patient rule for each scope;
- protocol-approved empirical risk ceiling and exact support criteria;
- permitted deterministic candidate-cutoff rule, score comparison/equality rule, tie rule and constant-score behavior;
- disclosure permissions for aggregate counts/metrics;
- frozen status mapping: one TRUST cutoff, valid below-cutoff cases CAUTION, invalid/unavailable/incompatible/not-ready cases DEFER;
- deterministic version/configuration identity and non-success handling.

All numerical settings are externally supplied by research-owner approval before outcome access. Missing required settings are `NOT_READY`.

### `PolicyEvidenceReference`

The new policy evidence's `dataset_id`, `manifest_reference`, manifest digest, dataset protocol/version, builder version, complete inventory digest, validation partition identity and verified source inventory. This entity is separate from the `dataset_reference` retained by Feature 005 and Feature 006 artifacts. It also records an authorized prior-history/linkage verification reference proving patient disjointness from upstream development/calibration and protected final-test populations, without exposing protected membership content.

### `OriginalReferenceReconstruction`

Private short-lived identity for Feature 004 reference reconstruction from the original, independently admitted Feature 003 training partition. It records only safe method/version/config and state digests needed to match the frozen Feature 005/006 `fitted_state_ids`. Raw vectors, categories, patient identifiers and evidence payloads remain local and are discarded after application.

### `PolicySignalProjection` (ephemeral)

Feature 004 `SignalFeatureRecord` generated inside Feature 007 from one independently admitted policy `PredictionRecord`, the exact original `SignalProtocol`, and the exact reconstructed original reference state. Stateless values use the established record-level extraction semantics; reference-based values apply only the original frozen reference. Its row key is derived from the new policy dataset identity and prediction fingerprint. Feature 007 does not trust a caller-created signal record or feature set as provenance proof and does not fit a new reference on policy rows.

### `VerifiedFrozenInputSet`

Private admission result containing verified typed Feature 005/006 artifact views, exact Feature 001 compatibility, verified original Feature 003/004 binding, new policy evidence identity, and passed verifier evidence. It is produced only after every shared trust/inventory check succeeds. It does not contain or expose patient scores.

### `PolicySelectionObservation` (ephemeral only)

Internal one-per-patient/scope projection of the protocol-selected index assessment, private frozen correctness-estimator score, verified binary correctness target, and opaque linkage used only for eligibility. It is never exposed, logged, added to estimator predictors, or serialized. Group and target values are removed before public outcome construction.

### `PolicySelectionSummary`

Aggregate exact-scope summary: eligible patient count and permitted support counts; selected patient count; empirical risk/coverage or explicit undefined state; protocol risk ceiling reference; selected cutoff method/value if disclosure is permitted; candidate count; deterministic tie decision; limitations and reason codes. No patient/row values.

### `SelectivePolicyArtifact`

Deeply immutable, canonical, versioned, selected-but-unevaluated policy record containing:

- exact model/version/label and Feature 001 registry compatibility references;
- Feature 005 estimator digest/version/family/schema/preprocessing and original training provenance;
- Feature 006 calibrator digest/method/mapping version and original calibration provenance;
- Feature 004 method versions and original fitted-state IDs/digests;
- new policy dataset/manifest/protocol/inventory and disjointness evidence references;
- Feature 007 protocol/version/configuration, cutoff semantics and one-cutoff status mapping;
- aggregate empirical selection results allowed by disclosure policy;
- lifecycle markers: policy selection evidence spent; independent final evaluation incomplete; protected test not accessed; non-deployable; clinical validity not established.

It excludes patient/group/assessment/occurrence IDs, row-level score or target, raw observation, restricted manifest, protected data, trusted verifier payload and fitted sklearn instance. A digest provides integrity only, not origin or durable persistence.

### `PolicySelectionOutcome`

One scope's status, fixed safe reason code, optional `SelectivePolicyArtifact`, and permitted aggregate summary. Successful status is `SELECTED_UNEVALUATED`; non-success has no artifact. Non-success categories distinguish at least `NOT_READY`, `INSUFFICIENT_EVIDENCE`, `INVALID_INPUT`, `INCOMPATIBLE_INPUT`, and `NO_FEASIBLE_CUTOFF` (or a documented mapping to the existing safe status model).

## State transitions

`unverified inputs → admitted exact-scope evidence → private score projection → protocol cutoff selection → selected-but-unevaluated artifact`.

Any failed shared trust or inventory check stops before score construction. A scope-specific inadequate evidence or no feasible nonempty selection yields a safe non-success and no artifact. Feature 007 has no transition to independently evaluated, deployable, or runtime-applied.
