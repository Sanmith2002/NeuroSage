# Data Model: Patient-Grouped Safety Dataset Builder

This model is supplemental to immutable Feature 001 registrations and Feature 002 collection values. It does not add fields to their contracts. Opaque patient references, source evidence references and full partition manifests are sensitive controlled data.

## Identity and supervision inputs

### TargetDefinition

Versioned meaning of one binary research outcome.

- `target_id`, `target_version`: exact stable identity.
- `positive_meaning`, `negative_meaning`: source-independent outcome semantics.
- `population_scope`, `observation_window` or `prediction_horizon`: applicability and time boundary.
- `outcome_coding`: explicit source value to positive/negative meaning mapping.
- `provenance`: source contract/version and controlled evidence reference.
- Invariants: exactly two declared outcome meanings; no threshold or disease meaning is inferred from model label text.

### TargetBinding

Declares compatibility between one target and one exact registered label.

- `target_id`, `target_version`.
- `model_id`, `model_version`, `label_id`.
- `target_positive_to_label_class`, `target_negative_to_label_class`: each maps to the exact Feature 001 `positive_outcome` or `negative_outcome`.
- `scope_compatibility`: population and timing compatibility declaration.
- Invariants: exact model/version/label lookup must succeed; no latest-version, component-version or display-name fallback.

### OutcomeCandidate and OutcomeVerification

An `OutcomeCandidate` contains only the source-provided supervised value and association needed for a verification attempt:

- `source_namespace`, `source_record_ref` (opaque), `patient_ref` (namespace-qualified), `assessment_ref` (source-qualified), `label_id`.
- `target_id`, `target_version`, `outcome_value`, `observed_at`, `source_contract_id`, `source_contract_version`, `content_ref`.

The configured trusted research verifier executes the check and returns an immutable `OutcomeVerification` with:

- checked `content_ref`, outcome source/contract version and exact association/target scope;
- authority, verification method, evidence reference and check time;
- state (`verified`, `rejected`, `unavailable`, `stale`, `conflict`) and safe reason code;
- correction/conflict lineage and declared limitations.

An identifier, claim, digest or caller flag alone is not a verification. The check must be produced by the configured integration operating against its independently controlled source evidence. Only `verified` checks matching every supplied field are eligible.

### IndependenceEvidence

Supplemental provenance about how the primary classifier's training, tuning, calibration and other development data relate to the safety outcome cohort.

- exact model/version/label and target scope;
- versioned development-cohort/source and processing lineage references;
- executed check result, authority/method, evidence reference and limitations;
- protocol-specific independence status (`eligible`, `overlap`, `unknown`, `conflict`).

`unknown`, conflicting or unverifiable history cannot support an independence-qualified dataset. The builder does not infer independence from dates, cohort names or source claims alone.

### EvidenceTimingDeclaration

Supplemental source evidence associating a prediction and any evidence used as candidate material with its availability at prediction time.

- exact prediction source key and occurrence;
- primary prediction time or explicit time scope;
- evidence category/selector and `available_at` or source-attested availability interval;
- source, contract version, check evidence and state (`verified`, `unavailable`, `conflict`).

This is not a Feature 002 field. Unknown or post-outcome material is excluded when the approved eligibility protocol requires prediction-time availability.

## Patient linkage and protocol

### PatientLinkageDeclaration

Authorized versioned opaque equivalences and cohort overlaps.

- `linkage_id`, `linkage_version`, authorized custodian/source, scope and evidence reference;
- entries map `(source_namespace, patient_ref)` to an opaque `patient_group_ref`;
- known cohort-overlap declarations and their source/version scope;
- executed `LinkageVerification` result bound to the declaration content/version and scope.

Invariants: duplicate source-qualified aliases, conflicting groups, malformed scopes or check/declaration mismatch fail closed. Missing cross-source mappings remain unknown; namespaces are never silently treated as disjoint. The builder performs no patient identity matching.

### EvaluationProtocol

Versioned study rules for inclusion, partitions, adequacy and protected-test handling.

- `protocol_id`, `protocol_version`, target/population and eligible registered-model/label scope;
- source, independence, evidence-timing and optional-evidence requirements;
- partition mode: supplied opaque patient-group assignments, or deterministic allocation configuration with explicit seed, role allocation, allowed strata, and stable algorithm version;
- required site/time isolation and other hard constraints;
- scope-specific adequacy criteria, limited-data status behavior and permitted summary outputs;
- final-test assembly, access/release and cross-version reuse conditions;
- transformation lineage policy and permitted use of each partition.

Invariants: all four roles are explicit; no universal ratios or minima; no seed search or constraint weakening; any infeasible assignment fails with a scoped readiness result.

### PriorAssignmentManifest

Controlled prior lineage supplied by the custodian for related-build conflict checks.

- dataset/protocol versions and opaque group-to-role assignments;
- protected final-test membership, source/cohort scope, lineage and permitted lifecycle state;
- manifest content/version reference.

Prior protected assignments cannot silently change because of a new seed, source alias, contributor or dataset version. Changed protocol or population requiring reassignment must follow the declared authorized lifecycle and create a traceable new artifact.

## Outputs

### CorrectnessExample

One accepted prediction/outcome join; model/version/label remain the unit even for overlapping component labels.

- exact Feature 002 `PredictionRecord` or an immutable detached projection preserving association, source key, primary output, source provenance and all evidence items/states;
- exact `TargetDefinition`/`TargetBinding` identifiers;
- verified binary outcome mapped to registered class meanings;
- `correctness_target` equal to `1` when `record.primary.predicted_class` equals the mapped verified class, otherwise `0`;
- patient group reference and eventual partition role in controlled data;
- verification, independence and eligibility lineage references.

Ground truth, correctness, verification, patient group, audit and partition values are excluded from prediction-time predictor material. No probability or score is converted into the correctness target.

### ExclusionRecord and DatasetReadiness

- `ExclusionRecord`: source-qualified controlled reference, safe reason code, protocol/eligibility scope and stage; no patient content in ordinary summaries.
- `DatasetReadiness`: `ready`, `NOT_READY` (missing protocol/trusted verification prerequisites), or `INSUFFICIENT_EVIDENCE` (declared adequacy/feasibility fails), with applicable model/version/label/population scope and safe reasons.
- A readiness result is not a clinical-safety claim and cannot make an excluded row eligible.

### PartitionedDataset and ProtectedTestArtifact

- development partitions: training, validation, calibration;
- separate protected final-test artifact with its own protocol state and handling boundary;
- all associated rows, visits, labels and contributors for one `patient_group_ref` share one role;
- exact duplicates do not increase examples/patient counts; distinct repeats preserve occurrence and eligibility lineage.

The Python package does not implement access control. The caller/custodian stores and releases the protected artifact according to the protocol. Ordinary build summaries do not return its rows or outcome/correctness distributions before the protocol's release condition.

### DatasetManifest

Immutable controlled artifact for reproduction and conflict detection:

- dataset/protocol/builder versions and build configuration;
- input content references and source/collection provenance;
- exact model/version/label registrations, target definitions/bindings and verification lineage;
- primary model independence and patient linkage versions/check references;
- inclusion/exclusion rule versions and controlled per-record audit references;
- partition mode/configuration/seed or supplied assignment reference, group assignments and prior protected history;
- outcome/evidence timing and preprocessing/transform declarations;
- protected-test lifecycle state and permitted reuse.

The full manifest may expose sensitive opaque group references and is treated as restricted. Ordinary reports contain only protocol-permitted aggregate status/counts. A canonical serialization digest can identify a manifest version or detect change; it is not proof of source identity, truth or linkage.

## State flow and invariants

1. **Candidate**: admitted Feature 002 record plus target, outcome, timing, independence and linkage declarations.
2. **Validated**: exact registration and all required executed check records match candidate scope; malformed, contradictory, duplicate or unverified joins move to exclusion.
3. **Eligible**: primary-time semantics and protocol inclusion requirements pass. Optional evidence states remain unchanged; optional invalid evidence is not silently upgraded or converted.
4. **Assigned**: opaque patient group receives exactly one protocol role after duplicate, overlap and prior-manifest checks.
5. **Published**: immutable dataset, protected-test artifact, controlled manifest and safe summary are returned. Adequacy failure or missing prerequisite produces `INSUFFICIENT_EVIDENCE` or `NOT_READY`, not an apparently ready training dataset.

At every transition, Feature 001 and Feature 002 values remain immutable and unchanged. No transition performs inference, safety feature extraction, fitting, calibration, policy selection, or assessment.
