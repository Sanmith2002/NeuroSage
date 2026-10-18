# Data Model: Feature 004 Safety Signals

All public values are immutable or defensively detached. These records supplement Feature 001–003 and do not add fields to `PredictionRecord`, `CorrectnessExample`, `SafetyContext`, `SafetyAssessment`, `ModelAdapter` or `AdapterCapabilities`.

## Identity and dataset inputs

### SignalSourceKey

Exact key `(model_id, model_version, label_id)` resolved through Feature 001 `ModelRegistry.get_metadata`. It is copied into every `SignalResult` and `FittedSignalState`. Component ID is optional provenance only; it is never a substitute for contributor identity.

### Feature003DatasetReference

Minimal immutable reference supplied alongside an ordinary Feature 003 `DatasetBuildResult`:

- dataset ID, protocol ID/version, manifest reference, optional verified manifest digest, Feature 003 builder version;
- only exact identifiers and approved source scope; no patient rows or group IDs.

Feature 003 may return a reference without durable persistence. Feature 004 records precisely the reference and receipt evidence supplied; it makes no persistence claim from a reference or accepted status alone.

### SignalDatasetVerification

Result of an explicitly injected trusted `DatasetInputVerifier` call. Binds the canonical detached development input fingerprint, readiness, exact dataset/protocol/manifest reference, exact training/validation/calibration partition scopes and verification authority/method/evidence reference. A boolean, digest supplied by the caller, or caller-created typed value is not independently verified evidence. The host integration must check against independently controlled Feature 003 build or custodian evidence. Missing, mismatched, stale, incomplete or unverifiable checks yield `not_ready` and no fitted state.

The ordinary Feature 003 result does not include protected rows or the complete sensitive manifest. The verifier boundary does not change that contract.

## Method and fitting configuration

### SignalMethodConfig

Immutable, versioned configuration for one dimension/method:

- `dimension`, `method_id`, `method_version`, `value_semantics`, `parameters`;
- exact registered source scope or explicit compatible scope;
- required evidence categories, expected states and interpretation/schema identifiers;
- preprocessing identity and reference scope when fitted;
- supported classifier forms and declared limitations.

Parameters are protocol-approved before a run. Examples include entropy/JSD log base, JSD pair/aggregation rule, kNN metric and `k`, domain category field/mapping version, and any approved method-specific support criteria. No default clinical threshold or universal minimum is implied.

### SignalProtocol

Versioned immutable run protocol containing approved method configs, accepted input dataset/protocol/manifest reference, exact model/version/label scope, evidence/schema compatibility, run configuration and method-specific adequacy. It separates patient predictor values from partition roles and supervision metadata.

### GroupedCrossFitConfig

Internal reference-training configuration:

- algorithm ID/version, `fold_count`, one fixed `seed`, training partition reference;
- stable deterministic group assignment rule: UTF-8 encode the protocol seed and opaque patient-group reference, hash `seed_bytes || NUL || group_ref_bytes` with SHA-256, interpret the digest as an unsigned big-endian integer, then take modulo the declared fold count;
- eligibility/support criteria declared by protocol.

One assignment is made per patient group and reused across all that patient's visits, labels and contributors. Patient-group references are used only for grouping, reference exclusion and controlled audit; they are never stored in feature values or ordinary run output. There is no alternate-seed search. If a protocol supplies explicit assignments instead of the hash rule, the verifier must establish complete, unique coverage of the training patient groups; missing assignments are not inferred or filled.

## Signal output entities

### SignalResult

One result for one exact source key, assessment occurrence, dimension and method version:

- `source_key`, `dimension`, `method_id/version`, signal-level `state`;
- optional immutable scalar/structured `value` with explicit semantics/units or representation;
- lineage references to Feature 002 evidence and (when fitted) the exact reference state;
- method parameters/version, preprocessing/evidence schema, applicable timing/scope;
- privacy-safe reason code and limitations.

Signal state values: `available`, `unsupported`, `missing`, `unavailable`, `invalid`, `insufficient_evidence`, `not_ready`. `available` for explanation in V1 denotes metadata/applicability only, never a numeric reliability judgment. Source Feature 002 states remain preserved and independently traceable.

### EvidenceCoverageProfile

Structured stateless result that maps each method-declared evidence prerequisite to its preserved Feature 002 state and a validation outcome. It does not include raw evidence payloads, patient identity, outcomes or class correctness. Coverage is not compressed to a universal score.

### CohortSupportSummary

Controlled, non-predictor metadata for one exact `SignalSourceKey` and Feature 003 training scope:

- unique patient-group support;
- correct/incorrect class support only where the approved method/protocol requires it;
- method-specific criteria, observed support and readiness result.

It never pools different contributors, versions or labels. Counts are not appended to patient-level predictor rows and are disclosed only where protocol/privacy rules permit.

### SignalRowKey and SignalFeatureRecord

`SignalRowKey` is a run-scoped opaque key for aligning one Feature 003 example to its extracted result. It is not a Feature 002 source contract change and contains no patient/group identity. The row mapping is retained separately from predictor values.

`SignalFeatureRecord` contains the row key and immutable mapping/tuple of predictor `SignalResult` values only. It excludes target, outcome, correctness, patient/assessment/occurrence references, group key and partition assignment. Feature sets retain separate train, validation and calibration collections; partition role is held by their enclosing controlled collection, not copied into features.

### FittedSignalState

Immutable state for a reference-based method:

- exact source key, method ID/version and parameter set;
- Feature 003 dataset/protocol/manifest reference and training-only scope;
- representation/category schema, preprocessing identity and reference population;
- final training reference data required for application (vectors or approved category vocabulary);
- cross-fit algorithm/version, fold count and seed provenance;
- supported compatibility key and safe content reference/digest for change detection.

State does not contain outcome/correctness targets, validation/calibration values, protected data or patient-group identifiers. Restricted representation/category values remain in controlled state memory and are not emitted in ordinary run summaries. State is never auto-reused across model/version/label, preprocessing, schema or cohort mismatch.

### SignalFeatureSet

Immutable collection of training, validation and calibration feature records; source/dataset/protocol/manifest identities; cohort support summaries under permitted privacy rules; readiness/exclusion codes; fitted-state references; and `SignalRunManifest`. No protected row/value is a member.

### SignalRunManifest

Privacy-safe reproducibility record: dataset/protocol/manifest reference, exact source keys, method/state versions and parameter identifiers, preprocessing/schema identities, one cross-fit seed/fold config, safe counts, state references/digests and exclusions. It contains no protected rows, patient IDs/group keys, raw input, outcome/correctness values or restricted manifest content.

### ProtectedApplyRequest and ProtectedApplyReceipt

`ProtectedApplyRequest` passes only frozen state references, exact dataset/protocol/manifest scope and approved method scope to an injected custodian integration. It does not carry protected rows. `ProtectedApplyReceipt` is a detached safe status/reference; it contains no transformed protected values, rows, outcomes or correctness distributions. The custodian is responsible for access and restricted artifact handling. The core has no protected retrieval API and no storage guarantee.

## Relationship and state flow

1. **Input**: accepted Feature 002 record and exact Feature 001 metadata, or a ready Feature 003 development result plus exact dataset reference and successful trusted input check.
2. **Stateless extraction**: evidence coverage, entropy, modality JSD, and explanation metadata; missing prerequisites produce explicit states.
3. **Cross-fit reference extraction**: use only eligible Feature 003 training predictor evidence; assign each patient group to one fixed fold; fit reference on other folds; score the held-out group; fail the scope if protocol-declared adequacy is infeasible.
4. **Final state fit**: fit on full eligible Feature 003 training predictor evidence after cross-fit rows are created. Keep state immutable and scoped.
5. **Development application**: transform validation/calibration with frozen state only. Emit row-key-aligned predictor records and a safe manifest.
6. **Protected application**: optional separate custodian-side apply-only operation with frozen state. No protected values flow back into ordinary API objects.

At every stage, exact source identity is retained; missing or invalid evidence never becomes zero; supervision and patient grouping never enter predictor values; no operation assesses safety or changes Features 001–003.
