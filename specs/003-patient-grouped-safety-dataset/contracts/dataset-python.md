# Python Contract: Feature 003 Dataset Builder

This describes the implemented in-process library boundary. It consumes Feature 001/002 public values and introduces supplemental supervised dataset records. There is no REST endpoint, registry migration, adapter change, safety estimator or clinical adjudication service in Feature 003.

## Public construction boundary

```python
DatasetBuilder(registry, trusted_verifier)

builder.build(
    predictions,
    outcomes,
    target_definitions,
    target_bindings,
    linkage_declaration,
    protocol,
    *,
    prior_manifests=(),
    timing_declarations=(),
    independence_evidence=(),
    transformation_declarations=(),
    protected_artifact_handoff=None,
    manifest_handoff=None,
    source_namespaces=None,
    group_attributes=None,
) -> DatasetBuildResult
```

Inputs are Feature 002 `PredictionRecord` values; normalized supplemental outcome/target, timing, independence and linkage values; and an approved versioned `EvaluationProtocol`. A source-specific trusted integration is explicitly supplied to the builder. It performs verification calls against independently controlled evidence and returns immutable scoped check records. Implementations must not accept a caller-provided pass Boolean, an identifier match or a digest as proof.

The builder uses exact `ModelRegistry.get_metadata(model_id, model_version)` lookups. It does not call `resolve_usable`, attach/reload models, call `ModelAdapter.predict*`, or alter collection records. One output example is keyed by exact `(model_id, model_version, label_id)` plus assessment/occurrence; overlapping component labels remain separate.

Before eligibility checks, the builder calls `trusted_verifier.verify_prediction_admission(prediction)` for each Feature 002 record. The immutable `PredictionAdmissionVerification` binds the SHA-256 fingerprint of the complete canonical record serialization, exact source key, patient/assessment/occurrence association, provenance mode, state, authority, method and evidence reference. A digest or typed result is not proof by itself: the explicitly configured integration must check the exact record against independently controlled Feature 002 admission evidence. Missing, rejected, mismatched or unverifiable admission excludes the record; if none remain, the result is `NOT_READY`. Caller-constructed records and self-asserted provenance fields cannot create admission evidence.

Live `PredictionRecord` values do not carry a source namespace in the unchanged Feature 002 contract. The caller may provide `source_namespaces`, keyed by the exact prediction fingerprint, or the verified linkage declaration may identify one unambiguous namespace for that patient reference. The exact alias set is passed to the trusted linkage verifier. A missing, conflicting or ambiguous namespace, including the literal `unknown`, yields `NOT_READY`; namespaces are never defaulted or treated as interchangeable. Precomputed source-contract identifiers may supply a namespace when the declaration and trusted linkage check agree.

## Trusted verifier boundary

The integration is trusted configuration supplied explicitly by the research application/operator. The implementation is responsible for accessing the appropriate independent source or custodian evidence and executing the claimed checks. Safira validates each immutable result's type and exact checked scope; it does not independently establish the authority's truth or promise universal verification.

Planned operations:

```python
trusted_verifier.verify_prediction_admission(
    prediction
) -> PredictionAdmissionVerification

trusted_verifier.verify_outcome(
    outcome, prediction, target_definition, target_binding
) -> OutcomeVerification

trusted_verifier.verify_independence(
    prediction, model_metadata, independence_evidence, protocol
) -> IndependenceVerification

trusted_verifier.verify_linkage(
    linkage_declaration, candidate_patient_refs, protocol
) -> LinkageVerification

trusted_verifier.verify_prior_history(
    prior_manifest, requested_scope, protocol
) -> PriorHistoryVerification
```

Each returned check is an immutable record bound to exact content/source version, source-qualified association, label/target, linkage or prior-history scope, check method/authority/evidence reference, timing and declared limitations. `PriorHistoryVerification` must bind the actual prior-manifest content/version and origin/source to the requested and declared scope, completeness evidence/coverage basis, and relevant protected-test memberships. The builder compares every check binding with the supplied values and current protocol. A caller-provided completeness flag, identifier or digest alone is not verification. Missing, partial, conflicting, stale, revoked under the source protocol, out-of-scope or unverifiable history remains unknown and cannot establish cross-version protection; when verified coverage is required by protocol, the build is `NOT_READY`. Other failed checks fail closed for eligibility. Exceptions are translated to fixed safe reason codes; arbitrary external error text is not retained.

Outcome truth, model-development independence and patient linkage are separate checks. A successful outcome check does not imply independent supervision; an independence record does not verify an outcome; a linkage mapping does not establish either one.

## Controlled manifest handoff

`manifest_handoff` is a separate, explicitly injected custodian integration. After constructing the full immutable `DatasetManifest`, the builder passes it to `manifest_handoff.accept(manifest, protocol, manifest_reference)`. The integration persists or otherwise controls the manifest and returns a `DatasetManifestReceipt`; only that detached receipt and the digest reference may appear in `DatasetBuildResult`. The manifest itself, including opaque patient assignments, is never returned in an ordinary development result or serializer. If no manifest handoff is supplied, the builder can return a digest reference but the caller cannot recover the manifest from Feature 003; callers requiring reproducible persistence must supply the authorized handoff. This adds no database or storage service.

## Protected-artifact handoff

`protected_artifact_handoff` is a separate explicit integration supplied for the build by the authorized custodian. Its single operation accepts the protected artifact only when the protocol permits assembly and returns a detached receipt/status:

```python
protected_artifact_handoff.accept(
    artifact, protocol, manifest_reference
) -> ProtectedArtifactReceipt
```

The handoff owns restricted persistence and release under the study protocol; Feature 003 does not implement a storage service or access control. The row-bearing artifact is not returned through `DatasetBuildResult`, ordinary serialization, logs, or development-facing APIs. A missing required handoff prevents publication of a completed build and yields `NOT_READY`.

## Core value contract

The `safira.dataset` package exports frozen value types described in [data-model.md](../data-model.md), including `PredictionAdmissionVerification`, `DatasetManifestReceipt`, `DatasetManifest`, and `DatasetBuildResult`. `ProtectedTestArtifact` and `DatasetManifest` are passed only to their separate custodian handoffs; neither is a field of `DatasetBuildResult`.

### Correctness derivation

1. Verify the outcome and exact target association through the injected trusted integration.
2. Resolve the exact immutable registered model version and label.
3. Validate target positive/negative meanings against the registered positive/negative class meanings using explicit `TargetBinding`.
4. Compare the mapped verified class string with `PredictionRecord.primary.predicted_class`.
5. Store integer `1` for equality and integer `0` for inequality.

The builder never re-evaluates `primary.value`, classifies a score, uses calibration/confidence as correctness, or modifies an existing mapping.

## Partitioning and protected-test behavior

- A protocol names training, validation, calibration and protected final-test roles and defines supplied assignments or a deterministic allocator with explicit configuration.
- Supported constraints are `site_isolation="same_partition"` (all groups from one site share a role), ISO-8601 timezone-qualified `time_windows` with inclusive start/exclusive end bounds by role, and `allowed_strata` membership. `group_attributes` supplies opaque group-to-site/time/stratum values; it contains no patient identifiers. Supplied assignments are checked against every declared constraint. Deterministic allocation hashes each unconstrained group once, or each site once when site isolation is active; time windows determine the matching role. It never attempts alternative seeds or tunes eligibility against protected outcomes. Missing required group metadata returns `NOT_READY`; unsupported constraint names return `NOT_READY` with `unsupported_partition_constraint`; unsatisfied supported constraints return `INSUFFICIENT_EVIDENCE`.
- Every visit, occurrence, label, contributor and source alias in a patient group receives one role across all related dataset views.
- Prior sensitive manifests are checked for protected membership or assignment conflicts using `verify_prior_history` against independently controlled custodian history. The check covers origin, source/version, declared and requested scope, completeness evidence and relevant protected-test membership. A self-asserted complete manifest is insufficient. Missing or unverifiable history remains unknown and cannot support a cross-version protection claim; protocol-required verified history yields `NOT_READY` when unavailable.
- Protected final-test rows are never fields of `DatasetBuildResult`, any ordinary serializer, or development-facing view/API. When the protocol authorizes assembly, the builder sends the row-bearing artifact only to the explicit `protected_artifact_handoff` supplied for that build. The handoff accepts the artifact under the custodian's control and returns only a detached non-sensitive receipt/status; the ordinary result contains that receipt/status, never the artifact or its correctness targets. Protocol-permitted integrity/structural summaries are explicitly listed.
- Feature 003 does not implement file-system access control, storage, or assert that later safety models are frozen. The custodian-controlled handoff implementation owns persistence and authorized release/reuse; no storage service is added.

## Immutability, privacy, and manifest contract

Accepted values are deeply immutable or own defensive copies of all nested inputs. Mutating original declarations, source values or returned serialization cannot mutate accepted examples, assignments or manifests. Public serialization is detached. Manifests containing patient-group references, source associations or protected membership are sensitive controlled artifacts. Tests inspect the complete `DatasetBuildResult` object and all ordinary serialization surfaces to ensure they contain no protected rows, outcomes or correctness targets. Ordinary summaries and errors contain only safe categories, approved aggregate scope/count information, and no identifying patient content, raw clinical data, row-level trace or protected outcome distribution.

Canonical serialization may use the standard library and a digest for deterministic comparison/change detection. Such a digest is not source proof, outcome verification, patient identity evidence or authorization.

`PriorHistoryVerification.protected_membership` is normalized to a tuple of nonempty opaque references at construction. Mutating a caller-owned list after construction cannot change the accepted verification result.

## Adequacy scope

Global criteria such as `minimum_examples` describe the declared overall build scope. Per-label criteria (`minimum_examples_per_label`, group counts, outcome counts, and correct/incorrect support) are evaluated independently for every exact `(model_id, model_version, label_id)` key; records from different contributors or versions never satisfy one another's per-label requirement. `EvaluationProtocol.adequacy_by_source` may add exact-key criteria, for example `{("model-a", "v2", "label-x"): {"minimum_examples": 20, "minimum_correct_predictions": 5}}`. No defaults or universal minima are introduced.

## Error and readiness contract

Planned typed categories (exact names may be refined during task generation):

| Category | Trigger | Result |
|---|---|---|
| `InvalidDatasetInput` | malformed/duplicate records, targets, protocol or association | no affected example or dataset published |
| `DatasetVerificationFailed` | outcome, independence, linkage or required prior-history check absent, mismatched, stale, partial, conflicting or unverified | affected scope excluded or `NOT_READY`; no correctness target or cross-version protection claim |
| `DatasetCompatibilityError` | exact registration/label/target semantics conflict | no affected example published |
| `PatientGroupingConflict` | alias maps to conflicting groups, unresolved required overlap, or prior assignment conflict | no combined partition claim; no silent reassignment |
| `DatasetLeakageError` | outcome-derived/post-outcome feature, held-out transform fitting, or prohibited final-test use | reject affected scope or return non-ready with safe reason |
| `DatasetProtocolError` | missing/unsupported protocol version or inconsistent roles/constraints | `NOT_READY` |
| `DatasetStorageError` | not introduced by core Feature 003; reserved only if a later approved persistence adapter is added | not applicable to in-memory contract |

`DatasetBuildResult` distinguishes a protocol-ready build, a `NOT_READY` prerequisite failure, `INSUFFICIENT_EVIDENCE` under a declared adequacy/feasibility rule, and record-level exclusions. It may contain development partitions, safe readiness/exclusion summaries, a controlled manifest reference, and a detached non-sensitive protected-artifact handoff receipt/status. It never contains the protected artifact or protected row values. If the protocol produces a protected artifact but no authorized handoff is supplied, the builder returns `NOT_READY` and does not publish ordinary development outputs as a completed build. Neither success nor readiness indicates clinical validity or safety.

## Compatibility examples

1. A standalone one-label classifier and a multi-label registration use identical target-join rules; each label resolves against the exact registration and class mapping.
2. Two independently registered contributors with the same `label_id` produce distinct examples retaining their own source keys, target bindings and provenance.
3. Live and trusted precomputed Feature 002 records may be consumed under their existing distinct provenance assurance; an unverified precomputed claim or `input_verification="unavailable"` alone does not satisfy any new outcome/linkage verification requirement.
4. Missing optional evidence remains in its Feature 002 five-state form when an otherwise eligible example is retained. Required evidence failure follows the protocol with an explicit exclusion reason.
5. Correctness is derived from `predicted_class`; a synthetic score crossing a hypothetical different boundary cannot change the target.
6. Changing an outcome value, target version, patient mapping, protected assignment, or source lineage changes or invalidates the build; an earlier accepted immutable manifest remains unchanged.
