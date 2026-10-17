# Research: Feature 001 Model Registration and Registry

**Date**: 2026-10-15

**Inputs**: [specification](spec.md), [Safira Constitution v3.0.0](../../.specify/memory/constitution.md), existing package and tests

## Decision 1: Persist metadata in an embedded SQLite catalog

**Decision**: Use Python 3.11's standard-library `sqlite3` with one configurable local database file in an ignored runtime artifact location. Persist a schema version and validated, canonical, declarative metadata only. Enforce `(model_id, model_version)` as the database key. Registration uses one transaction and a plain `INSERT`; a key conflict becomes an explicit duplicate-registration failure. Do not use `REPLACE`, an upsert, or a silent ignore. Use ordinary rollback journaling and durable commit settings; no WAL mode or external server is required for the specified catalog.

**Rationale**: The spec requires restart survival, immutable records, and at most one accepted record under competing registration attempts (FR-002, FR-007, FR-008). A local transactional catalog meets those requirements without a runtime dependency or service. Never serialize executable classifier or adapter objects, patient observations, predictions, or datasets. Validate stored metadata on reading. Corrupt/unreadable storage, unknown storage schema, invalid stored records, and lock/I/O failures are storage errors, not an empty catalog or an unknown model/version. Back up or migrate the catalog only through an explicit, later design.

**Alternatives considered**: An in-memory dictionary fails restart persistence. Atomic JSON files require cross-process locking, atomic update and durability handling on each supported OS; a whole-catalog JSON file also risks lost writes. Pickling executable objects creates unsafe loading and weak version compatibility. A client/server database and cloud service add unnecessary infrastructure. WAL mode adds sidecar lifecycle work without a demonstrated concurrency or latency need. SQLite's [Python 3.11 API](https://docs.python.org/3.11/library/sqlite3.html), [key constraints](https://www.sqlite.org/lang_createtable.html), and [atomic commit behavior](https://www.sqlite.org/atomiccommit.html) support the selected approach.

## Decision 2: Separate durable identity from live usable association

**Decision**: Keep `RegisteredModelVersion` immutable in the catalog. Hold a process-local binding of the exact classifier object, `ModelAdapter` instance, and their checked identity evidence under the same exact `(model_id, model_version)` key. `get_metadata` returns a validated metadata record even when unbound. `resolve_usable` returns the metadata, classifier, and adapter as one association only after successful `attach`; otherwise it raises a specific unavailable/mismatch error. A new process starts with no bindings and requires explicit reattachment. Never infer a latest version or locate an adapter by class name alone.

**Rationale**: This implements the approved restart and linkage clarifications (FR-005, FR-007, FR-009). It leaves executable objects out of persistent storage and avoids altering `ModelAdapter`, `SafetyContext`, or `SafetyAssessment`.

**Alternatives considered**: Persisting live Python objects contradicts metadata-only restart and is unsafe. Returning only metadata for downstream use spreads compatibility checks across future features. Automatic latest-version selection conflicts with exact-version safety-package binding.

## Decision 3: Require checkable artifact and adapter identities

**Decision**: Require a minimal owner-supplied `IdentityProvider` with an `identify_loaded_pair(classifier, adapter) -> IdentityEvidence` operation. `IdentityEvidence` contains the classifier artifact's SHA-256 fingerprint, the adapter implementation's SHA-256 fingerprint, and an actual Boolean `loaded_pair_verified` attestation. SHA-256 is computed over exact immutable artifact bytes; for a multi-file artifact, the provider hashes a deterministic manifest with normalized relative paths and file-content digests. For non-file-backed models, the owner/provider hashes an owner-defined deterministic representation of non-patient model state. The provider must attest that the supplied live classifier was loaded from the material fingerprinted and that the supplied adapter is the implementation fingerprinted. Registration stores the two fingerprints, not the provider, model, adapter, source bytes, or patient data. At registration and again on attachment, Safira compares the evidence with the declared identities and immutable record, and requires `loaded_pair_verified is True` before accepting or publishing a binding. No provider, unsupported evidence, unverifiable loaded-object association, or mismatch fails closed.

**Rationale**: A user-supplied name or version string alone cannot detect a different classifier or changed adapter code being attached under an earlier registration (FR-005, FR-006, FR-009). Deterministic digests give the registry a comparison key without prescribing a framework's serialization. A digest alone cannot prove the origin of an arbitrary live Python object. The classifier owner or trusted loader bears responsibility for linking the object to the checked immutable artifact and for the provider's attestation; Safira trusts that configured provider and fails closed if it cannot return verifiable evidence. This is an explicit provenance boundary, not a claim that hashing proves model behavior.

**Alternatives considered**: Accepting only caller-asserted names/digests without a trusted loader link does not verify the live pair. Requiring a particular pickle or framework checkpoint format would break model agnosticism; the owner-supplied provider may use exact artifact bytes or a deterministic owner-defined representation. Running a prediction to fingerprint a classifier would violate registration scope and could involve patient data. The provider is a small integration boundary, not a new method on or change to the existing adapter base class, and requires no external service or security infrastructure.

## Decision 4: Describe continuous outputs with the existing adapter methods

**Decision**: Each label declares binary verified outcome meanings, stable output selection, a continuous value type, a defined numeric scale or domain, increasing/decreasing positive direction, and a deterministic value-to-positive/negative class rule. Individual observed values must be finite; a non-probability score's declared domain may be unbounded. For a true probability, require `AdapterCapabilities.prediction_probability is True` and an implemented `predict_probability` override. For a non-probability continuous score, declare that the existing mandatory `predict` method returns that score and describe its domain and class rule. Never mark a non-probability score as a probability or place it in `SafetyContext.prediction_probability`. `predict` returning only hard 0/1 does not meet Feature 001's output requirement.

**Rationale**: The current `ModelAdapter` has `predict` and optional `predict_probability`, but no generic `predict_score`; `AdapterCapabilities` is frozen yet currently does not enforce Boolean field types. Registration can validate type, method availability, and declarations without patient calls (FR-001, FR-003, FR-004). Actual runtime output ranges and correctness need synthetic contract tests now and later validation where outputs are used. Primary prediction values are distinct from Safira's future reliability score and policy status.

**Alternatives considered**: Adding `predict_score` to the base adapter now would change an approved contract without a demonstrated need. Treating arbitrary scores as probabilities gives false semantics. Hard predictions alone lose the required continuous output. If future use requires class and non-probability score as two simultaneous method results, a separately justified adapter extension will be needed; Feature 001 does not silently introduce it.

## Decision 5: Validate declared schema and capability shape without clinical execution

**Decision**: Accept `supervised_single_label_binary_classification` with exactly one label or the existing `supervised_multi_label_classification` with at least two unique, nonblank stable label IDs. Zero labels and task/count mismatches are rejected. Validate explicit positive/negative meanings and exact output mapping for every label; validate identifiers and versions without trimming them; validate input/modality/preprocessing metadata as bounded declarative schema, including an explicit `none` preprocessing identity where applicable. Enforce actual `bool` values for every `AdapterCapabilities` flag and check that claimed optional methods are concretely implemented. Reject patient observations and arbitrary payload blobs. Registration and reattachment are metadata and identity operations; neither performs training, extraction, calibration, policy selection, or assessment.

**Rationale**: These checks address FR-001–FR-006, FR-011–FR-014 while preserving existing runtime behavior. Unsupported capabilities stay false/unavailable. Static checks can show only declared compatibility, not prove that all future outputs conform or that clinical evidence is sufficient.

**Alternatives considered**: Running adapters on clinical examples at registration would introduce patient-data access and assessment scope. Altering `AdapterCapabilities` globally just to reject non-Boolean values would rewrite an existing contract; the registry can validate its own input boundary.

## Decision 6: Verify with deterministic pytest scenarios

**Decision**: Use temporary database files, deterministic test-only adapters/classifier artifacts and a fake trusted identity provider, and pytest. Cover deep immutability against mutation through both original inputs and returned metadata; registration without labelled safety data or a package; exact input-schema, modality and preprocessing round-trips; exact lookup; a genuine subprocess restart with metadata retained and bindings absent; successful and failed reattachment; invalid schemas/output semantics/capability values; duplicate races using separate registry connections; storage failures; privacy-safe errors; and proof that registration never calls patient-facing adapter methods or safety setup. Run existing tests for regression. The review catalog for SC-002 contains at least three model IDs and three versions of one model; no numerical lookup-latency benchmark is introduced.

**Rationale**: This provides reproducible evidence for FR-001–FR-015 and SC-001–SC-004 plus SC-006–SC-007 (SC-005 was removed by clarification) without claiming clinical validation.

**Alternatives considered**: A latency target was expressly rejected during clarification. Clinical datasets are unnecessary and inappropriate for registry-contract verification.

## Remaining integration risks

- Artifact/adapter identity verification depends on a trustworthy integration supplied by the classifier owner or trusted loader. Digest equality proves equality of checked bytes or deterministic identity material, not the origin or behavior of an arbitrary live object. The configured provider must attest to the loaded-object link; Safira cannot independently prove that link generically. Usable access must fail when this link cannot be established.
- Static method and metadata checks cannot prove that a classifier actually emits continuous values for every label. Deterministic synthetic tests check integrations; later assessment/training features must validate observed output types and ranges before safety use.
- A later safety package must reference the exact immutable registry identity and compatibility metadata, but package storage, training, and deployment are outside Feature 001.

## Decision 7: Keep classifier cardinality separate from component composition

**Decision (approved scope, 2026-10-17)**: Support single-label binary classifiers and
multi-label classifiers as independently registered contributors to a component.
Use existing exact metadata and usable-pair operations for each contributor; preserve
`(model_id, model_version, label_id)` and the matching adapter declaration. Allow label
IDs to overlap across separate registrations without merging the contributions.
A missing, incompatible, or unattached source cannot be substituted or silently omitted
to claim a complete component output. No component entity, prediction execution,
aggregation algorithm, or clinical fusion policy is introduced into Feature 001.

**Rationale**: The number of component output labels does not describe any individual
classifier's label cardinality. Independent registrations already supply exact identity
and compatibility boundaries (FR-002, FR-004-FR-009, FR-015). An explicit new single-label
task token preserves the meaning of legacy multi-label records and rejects mislabeled
schemas. The same serialized fields suffice; no storage layout migration is planned.

**Verification**: Add synthetic all-single-label and mixed contributor acceptance
(SC-007), overlapping label IDs, explicit source failures, and both probability and
non-probability continuous-output cases. Extend restart, identity mismatch, immutability,
and duplicate-race regressions to the new eligible form. Existing provider checks and
the trusted-loader limitation in Decision 3 are unchanged.

**Handoff review**: The user-supplied `C:/Users/User/Downloads/PD Copathology Handoff.md`
confirms three independently trained binary classifiers behind one component output.
Its shared component version does not replace per-classifier identity verification.
Its output excludes decision thresholds, so the required per-label prediction-to-class
mappings cannot be assumed from that handoff. No default threshold or new mapping policy
is introduced. Actual PD onboarding needs authoritative identities and mappings; see
[scope-amendment.md](scope-amendment.md) for the full comparison and remaining integration
questions. External bundle files and reported results were not independently verified.
