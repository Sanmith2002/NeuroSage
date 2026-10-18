# Python Contract: Feature 004 Signals

In-process library contract for the clarified Feature 004 V1. Names are planning-level, but behaviors and data boundaries are normative. This contract adds no fields/methods to Features 001–003 or existing adapter/context/assessment types.

## Proposed public surface

```python
class SignalInputVerifier(Protocol):
    def verify_prediction(self, record: PredictionRecord) -> SignalInputCheck: ...
    def verify_dataset(
        self, result: DatasetBuildResult, reference: Feature003DatasetReference
    ) -> SignalInputCheck: ...

class SignalExtractor:
    def __init__(
        self,
        registry: ModelRegistry,
        protocol: SignalProtocol,
        verifier: SignalInputVerifier,
        *,
        protected_apply: ProtectedSignalApplyHandoff | None = None,
    ) -> None: ...

    def extract_record(self, record: PredictionRecord) -> tuple[SignalResult, ...]: ...

    def build_feature_set(
        self,
        dataset: DatasetBuildResult,
        reference: Feature003DatasetReference,
    ) -> SignalFeatureSet: ...

    def apply_protected(
        self,
        request: ProtectedApplyRequest,
    ) -> ProtectedApplyReceipt: ...
```

`SignalInputVerifier` must be an application-owned, explicitly injected integration. `verify_prediction` executes a check against independently controlled Feature 002 admission evidence and binds the exact prediction content fingerprint, source key, association occurrence, provenance mode and input scope. `verify_dataset` binds the exact detached Feature 003 development input fingerprint, ready state, dataset/protocol/manifest reference and train/validation/calibration scopes, and independently establishes Feature 002 admission for every embedded development `PredictionRecord`. Its verified row inventory binds each row's exact canonical prediction/evidence content or fingerprint, Feature 002 source key, association/occurrence, model/version/label, admission lineage, dataset identity and authorized partition. A trusted aggregate attestation is sufficient only if independently controlled evidence covers the complete exact row inventory and each row's Feature 002 admission lineage; otherwise the integration verifies every row individually. The verifier rejects rows that are missing, duplicated, substituted, altered after admission, stale, or inconsistent in source identity, association, dataset or partition. No row lacking this check may contribute to signal values, cohort-support claims, reference fitting, or a published feature set. An `accepted` status, typed dataclass, caller Boolean, digest assertion, manifest reference or source field alone is not evidence. The integration performs the external check; Safira validates exact returned scope and fails closed. There is no hidden global verifier or payload-selected implementation.

The verifier is necessary because Feature 002/003 public frozen dataclasses may be constructed by callers. Synthetic tests use an independent in-memory ledger; this is not deployment authentication. If no configured verifier exists or a check is missing, wrong-scope, stale, conflicting or unverifiable, signal values are not emitted and readiness is `not_ready`.

## Record extraction

`extract_record(record)`:

1. Check type and execute `verify_prediction`.
2. Resolve exact Feature 001 metadata using `registry.get_metadata(record.model_id, record.model_version)`. Check label ID, registered score type/scale/direction, class mapping, adapter/evidence declarations and preprocessing identity.
3. Validate source provenance and every evidence item against the same association and source key. Preserve the five Feature 002 states and each item's interpretation; do not consult mutable `SafetyContext` Boolean availability.
4. Emit independent V1 results for the configured dimensions. A signal failure does not discard another valid result.

The extractor never calls `resolve_usable`, never invokes the primary classifier/adapter, and never repeats prediction. Evidence is already collected by Feature 002. Any result is keyed by the exact model/version/label, not component identity.

## Stateless method behavior

| Method | Input/validation | Result |
|---|---|---|
| Evidence coverage | Immutable Feature 002 evidence states plus method prerequisite profile and optional interpretation. | Structured prerequisite-to-state profile. No scalar sufficiency score or raw evidence values. |
| Predictive entropy | `primary.value_kind == "probability"`; exact registered binary probability, finite in `[0,1]`. Log base is protocol-declared. | `H(p)=-p log(p)-(1-p)log(1-p)`; define `0 log 0=0`; record log base and probability calibration semantics. |
| Modality JSD | `modality_outputs` evidence is available; at least two modality probabilities validate against the same exact contributor, label, target, association, timing and compatible output/calibration semantics. | Pairwise `H((P_i+P_j)/2)-(H(P_i)+H(P_j))/2`; record log base and pair/aggregate policy. Never compare separate model contributors. |
| Explanation scope | Valid explanation metadata including method, target label/output, output space, calibration relation and source/timing provenance. | Structured metadata/applicability result only. No numeric explanation reliability. If metadata is incomplete, emit the corresponding non-value state. |

Repeated-output variation is optional and not required by the minimal public API. If enabled under a protocol, it requires valid same-input repeat provenance and compatible probability semantics; its defined descriptive variance is `R⁻¹ Σᵣ(pᵣ−p̄)²`. It is not decomposed into epistemic/aleatoric uncertainty.

## Reference methods

### Fit and cross-fit

`build_feature_set` requires a ready Feature 003 development result, exact `Feature003DatasetReference`, and a verified, row-complete dataset check. The caller's protocol and reference must agree on dataset/protocol/manifest scope. Every embedded prediction must have exact Feature 002 admission lineage within that dataset check before any row is used. All fit input is drawn from the `train` partition only and excludes outcomes, correctness targets, verification records, patient group IDs and partition roles from feature values.

For each exact source key and reference method:

1. Validate finite 1-D vectors or approved domain category codes, method/schema/preprocessing identity and declared protocol criteria.
2. Map each opaque patient group to one deterministic fold using the exact configured algorithm/version and one protocol seed. All rows across visits, labels and contributors for that group use the same fold.
3. For each fold, build the temporary reference from other folds and score only the held-out fold. A patient's full group is excluded, preventing self-neighbour or self-category support.
4. If a fold cannot satisfy protocol-declared support (e.g. fewer than `k` compatible reference vectors), return `insufficient_evidence` for that exact method/scope. Do not split groups, search another seed, borrow another contributor's reference or score against an in-sample reference.
5. After training-row features are produced, construct a final immutable reference from all eligible training predictor evidence. It is used only to transform permitted validation/calibration and later compatible inputs. Changing verified patient-group assignments may change folds and cross-fitted training scores, while every scored group remains wholly excluded; merely renaming opaque group references cannot change this final full-training reference when predictor evidence and configuration are unchanged.

Cross-fit assignment algorithm: UTF-8 encode protocol seed and opaque group reference; compute `SHA256(seed || NUL || group_ref)`; interpret digest as unsigned big-endian integer; fold is integer modulo the protocol's `fold_count`. Algorithm version and seed are recorded. If the approved assignment scheme is explicitly supplied in the protocol, verify it covers every training patient group exactly once and use it; do not supplement missing assignments or reassign to improve adequacy.

`fit_reference(dataset, reference, protocol) -> SignalFitResult` and `apply_reference(state, record, reference) -> SignalResult` may be exposed internally or as separate public calls; tasks may settle the exact wrapper. They must enforce the same input check, partition, identity, and state-compatibility rules as `build_feature_set`.

### Compatibility check

Before apply, compare exact:

- model ID, model version, label ID;
- method ID/version and immutable parameters;
- Feature 001 preprocessing identity and primary output semantics;
- Feature 002 evidence category/schema/interpretation and feature representation ID/dimension;
- Feature 003 dataset/protocol/manifest identity and declared reference cohort/time/domain scope;
- cross-fit/final-reference provenance and supported input population.

Any mismatch yields `not_ready` or a typed compatibility failure. Do not transfer fitted state across model versions, labels, contributors, schemas or cohorts automatically.

### Values and performance

V1 representation is a finite flat numeric sequence. kNN uses the protocol-approved metric (initial implementation may support Euclidean only) and a linear scan, O(N·d) distance work per query. No unrequested dependency/index. Invalid dimension/non-finite value is `invalid`; missing representation follows its Feature 002 state; a valid but undersized reference is `insufficient_evidence`. No distance threshold exists.

Domain state uses a privacy-approved canonical category vocabulary fitted only on training evidence. Apply returns `seen`/`unseen` category membership, not raw category, site ID, support count or shift probability. Training-row membership is cross-fitted so a group's own category cannot make it `seen` in its fold vocabulary.

## Signal-level availability and failure contract

Feature 004 result state differs from Feature 002 evidence state:

| State | Meaning |
|---|---|
| `unsupported` | Method or required adapter/source capability is not supplied. |
| `missing` | Expected evidence is absent from an otherwise valid record. |
| `unavailable` | Supported evidence was requested but could not be obtained. |
| `invalid` | Supplied evidence is malformed, non-finite, semantically conflicting or fails compatibility validation. |
| `insufficient_evidence` | Valid evidence does not satisfy the exact method's protocol-declared support needs. |
| `not_ready` | Required approval, trusted verification, compatible reference, manifest scope or custodian integration is unavailable. |

No state maps to numeric zero. Feature 002's `available/unsupported/missing/unavailable/invalid` record remains intact as lineage. Error messages use fixed safe codes and do not include patient values/IDs, explanations or restricted artifacts.

## Feature 003 alignment and output boundary

`build_feature_set` consumes only `DatasetBuildResult.development.train`, `.validation` and `.calibration` records. It does not retrieve the full manifest or protected rows. Rows are aligned using `SignalRowKey` in a separate map; no patient/group/partition/outcome/correctness field enters the predictor feature mapping. `CohortSupportSummary` is a separate controlled metadata field, evaluated per exact source key; any correctness-class counts are from training only and are not features.

The optional `ProtectedSignalApplyHandoff` accepts only a `ProtectedApplyRequest` naming an immutable fitted-state reference and exact dataset/protocol/manifest/method scope. The integration executes application in its custodian-controlled environment and returns `ProtectedApplyReceipt` only. No protected record or transformed signal value enters Feature 004 ordinary objects, serialization, logs or exceptions. The receipt proves only the integration's declared operation to the extent it actually checks it; it does not imply persistence unless the integration checks and declares that guarantee. No real integration exists currently.

## Immutability and privacy

Recursively detach all accepted method configurations, parameters, signal values, fitted reference values, lineage, feature rows and manifests. Freeze mappings/collections or own defensive copies. `to_dict()` returns detached output. Domain categories, row keys, references and fit state may be sensitive; only protocol-permitted opaque identifiers and safe digests/references appear in ordinary manifest/log output. Protected state and full domain vocabulary remain restricted to their declared control boundary.

## Typed errors

Proposed errors in `safira.signals.exceptions`:

- `SignalInputError`: malformed value, missing exact registration/label, invalid evidence or source mismatch.
- `SignalVerificationError`: absent, wrong-scope or unsuccessful trusted input check.
- `SignalCompatibilityError`: fitted-state/reference mismatch.
- `SignalProtocolError`: missing/invalid method or fold configuration, unsupported constraint.
- `SignalNotReady`: absent required approval/reference/custodian boundary.
- `SignalPrivacyError`: prohibited field or protected value supplied through an ordinary interface.

Method-specific insufficiency can be represented as `SignalResult(state="insufficient_evidence")` without an exception when independent results can continue. Unexpected internal failures translate to a fixed safe failure code.

## Protected-test custodian protocol

```python
class ProtectedSignalApplyHandoff(Protocol):
    def apply_frozen_state(
        self, request: ProtectedApplyRequest
    ) -> ProtectedApplyReceipt: ...
```

`ProtectedApplyRequest` contains references/configuration only; it does not contain `ProtectedTestArtifact`. The authorized custodian resolves the frozen state and Feature 003 protected artifact locally, checks exact manifest/partition/state compatibility, applies without fitting or tuning, persists the resulting restricted artifact if its policy requires, and returns only a detached receipt/status. An accepted receipt is not a durability guarantee unless the integration independently verifies and attests that specific guarantee. Ordinary Feature 004 has no protected retrieval operation.

## Compatibility and validation examples

1. Entropy for a synthetic probability is deterministic, distinguishes `p=0.5` from `p∈{0,1}`, and carries calibration semantics; a continuous score is not accepted.
2. Equal modality probabilities produce zero JSD; semantically mismatched modalities yield `invalid`/`unavailable`; overlapping labels from two classifiers remain separate and are never compared.
3. A synthetic kNN reference returns the declared k-th distance. Wrong vector dimension, nonfinite coordinates, preprocessing change, label/version change or different dataset reference prevents application.
4. A training patient's multiple visits/labels all map to one cross-fit fold and are all removed from that fold's reference. Fixed seed and grouping rerun identically; changed verified grouping may change fold assignments and cross-fitted scores without weakening exclusion. Renaming only opaque group references leaves the final full-training reference unchanged when predictor evidence/configuration are unchanged. Changing validation/calibration/protected data does not change fit state; no alternate seed is tried.
5. A `seen` domain category returns only allowed category state, not category/site label or support count. Training group is removed from its fold vocabulary.
6. Explanation with valid metadata produces metadata/applicability only. Missing method/target/output-space prevents any reliability number.
7. Mutating caller mappings/lists, source evidence values or returned serialization cannot change accepted signal results/state.
8. Forged Feature 002 records, including a forged or altered prediction embedded in an otherwise accepted Feature 003 result, do not pass without an executed exact-row-scope trusted check. Caller booleans/digests, incomplete aggregate row attestations, missing/stale admission lineage, wrong association/source identity, or wrong manifest/partition checks fail closed. A positive case binds every exact embedded record and its Feature 002 admission lineage.
9. A custodian test double receives only frozen-state and exact-scope references; neither request nor ordinary receipt/result serialization contains protected rows or transformed values.
