# Proposed Python Contract — Feature 005

**Status:** Batch A (T001–T017) implemented; later batches remain planned. It adds a `safira.training` surface and does not change public Features 001–004, `ModelAdapter`, `AdapterCapabilities`, `SafetyContext` or `SafetyAssessment`. [Data model](../data-model.md) defines invariant details.

## Planned full orchestration surface

```python
class SafetyTrainingService:
    def __init__(
        self,
        registry: ModelRegistry,
        protocol: TrainingProtocol,
        input_verifier: TrainingInputVerifier,
    ) -> None: ...

    def train(
        self,
        dataset: DatasetBuildResult,
        signals: SignalFeatureSet,
    ) -> tuple[TrainingOutcome, ...]: ...
```

**Batch A implementation note:** T001–T017 currently implement `SafetyTrainingService.prepare(dataset, signals)`, which performs complete trusted admission, exact alignment, registry compatibility and per-scope eligibility only. The `train(dataset, signals)` operation above remains planned for later batches. No candidate is fitted and no successful estimator artifact can be published in Batch A.

`train` verifies the **complete** paired inputs before it returns any successful scope outcome, cohort-support assertion, selected estimator or artifact. It returns one outcome per protocol-authorized exact `(model_id, model_version, label_id)` scope in deterministic source-key order. It does not call primary classifiers, Feature 003 target builders, Feature 004 extractors or protected-test APIs. All ordinary outputs are privacy filtered. A top-level failed shared admission returns/raises a typed safe failure for all affected scopes; it never continues from an unverifiable partial inventory.

## Injected trusted-host verifier

```python
class TrainingInputVerifier(Protocol):
    def verify_inputs(
        self,
        dataset: DatasetBuildResult,
        signals: SignalFeatureSet,
    ) -> TrainingInputCheck: ...

    def verify_dataset(
        self,
        dataset: DatasetBuildResult,
        reference: Feature003DatasetReference,
    ) -> SignalDatasetCheck: ...

    def verify_prediction(self, record: PredictionRecord) -> SignalInputCheck: ...
```

The host controls verifier construction and an independently maintained acceptance ledger; a caller cannot supply a fabricated `TrainingInputCheck` in lieu of executing verification. `verify_inputs` must check that the exact Feature 003 development result and exact Feature 004 feature set/run were previously accepted by authorized integrations, including the complete embedded Feature 002 record lineage. The core still recomputes actual full-content fingerprints, full per-role inventories and every Feature 004 row key, checks exact registration and compatibility, and executes `verify_prediction` for every embedded record. A returned check contains authority/method/evidence references, exact dataset-build identity, full dataset/feature-set fingerprints, Feature 004 run/method/reference identities and exact row inventory. Feature 003 has no separate `dataset_version` or builder ID field: the exact build/version binding is the independently verified tuple of `dataset_id`, `manifest_reference` and manifest digest, `protocol_id`/`protocol_version`, existing `builder_version`, and complete row inventory. It must not be accepted if any field is absent, stale, self-asserted, inconsistent or mismatched. A check/digest is comparison evidence, not proof of the provider's independent control.

Trust limitation: the core relies on the configured host/provider. It cannot authenticate arbitrary malicious Python that controls the trusted host; the repository has no configured clinical ledger. Synthetic tests use a separately controlled fixture ledger and verify missing/mismatched/forged entries fail. No hidden global verifier or `verified=True` shortcut.

### Row-alignment and leakage contract

For every Feature 003 `CorrectnessExample` in `train`, `validation`, `calibration`, derive the expected Feature 004 `SignalRowKey` from the existing dataset ID, manifest reference and full prediction fingerprint. Require exactly one matching `SignalFeatureRecord` in the corresponding Feature 004 role and exact source key. Reject missing, extra, duplicate, cross-role or changed content; verify all embedded Feature 002 admissions independently. Verify patient-group disjointness across roles using restricted Feature 003 keys, including all visits/labels/contributors. Feature 005 builds a matrix from **train** and **validation** only; calibration is verified for completeness but never transformed or scored here. Protected final-test content is never accepted by this API.

The only supervised target is Feature 003 `correctness_target`. Patient/group keys are accepted only into trusted eligibility/disjointness checks. No target, outcome, group, row key, partition role, verification record or copied primary output becomes a predictor or enters learned preprocessing or candidate scoring.

## Configuration and outcome records

```python
@dataclass(frozen=True)
class TrainingProtocol:
    protocol_id: str
    version: str
    source_policies: Mapping[TrainingScope, SourceTrainingPolicy]
    # Source policy declares feature/method allowlist, state handling,
    # independent-group/class support, preprocessing, candidate requirements,
    # fixed logistic C/tol/max_iter and metric feasibility before validation.

@dataclass(frozen=True)
class TrainingOutcome:
    scope: TrainingScope
    status: TrainingStatus
    artifact: SafetyEstimatorArtifact | None
    reason_code: str | None
    limitations: tuple[str, ...]
```

All nested protocol values are defensively detached. Required scientific settings have no implicit numerical fallback. `NOT_READY` denotes missing approval/trusted verification; `INSUFFICIENT_EVIDENCE` denotes approved support unmet. `UNAVAILABLE_REQUIRED_EVIDENCE` denotes a required signal cannot be constructed. `INVALID_INPUT`, `INCOMPATIBLE_INPUT`, `COMPARISON_UNDEFINED` are separate non-success outcomes. Candidate-specific `FIT_FAILED`/`NONCONVERGED` appears only as safe candidate status; another candidate may win only under a predeclared policy. `SELECTED_BASELINE` and `SELECTED_LOGISTIC` are successful **intermediate** selections after a valid comparison. A single-class baseline-only description is non-success and has no artifact.

## Feature encoding contract

`FrozenFeatureSchema` fixes ordered predictors from approved Feature 004 `(dimension, method_id, method_version, semantics)`. Only finite available numeric values, approved nominal `seen`/`unseen`, and explicitly allowlisted typed availability indicators are encoded. Seven availability states remain distinguishable. `invalid`, `not_ready` or unverified values fail closed. `unsupported`, `missing`, `unavailable`, `insufficient_evidence` need explicit policy. Universally unsupported dimensions are omitted with recorded reason; a required all-missing feature yields non-success. Explanations, evidence provenance and primary outputs stay metadata.

When approved, `FrozenPreprocessingState` holds training-only numeric medians, mean/scale, fixed nominal/state one-hot order and constant/optional-column decisions. A filled numeric slot is always accompanied by a state indicator and is never presented as measured evidence. Same frozen transformation applies to validation. No fitting or selection from validation, calibration or protected data.

## Candidate and metric contract

- Baseline: `p = mean(y_train)` for the exact scope.
- Logistic: scikit-learn 1.7.1 L2 `LogisticRegression`, solver `lbfgs`, no class weighting, fixed positive protocol `C`/`tol` and positive `max_iter`, intercept enabled, no warm start. Two training correctness classes and approved group/class support are required; warnings, non-finiteness and failed convergence are explicit candidate failures.
- Compare valid predeclared candidates once on the same authorized validation rows by mean squared Brier, lower better; exact equality chooses baseline. AUROC/AP are secondary and undefined where class support/meaning is lacking. The protocol fixes any required comparison feasibility before validation. No second CV, seed search, refit or threshold choice.
- Validation metrics are tagged `selection_evidence`, not independent final performance. Repeated rows are correlated; no row-independent uncertainty claim.

### Training-fit isolation tests

An altered validation/calibration record that lacks fresh independent authorization must be rejected by full-service input admission. Do not reuse its previous admission as authorization for changed content. Separately test fitting independence either with independently reauthorized synthetic full-service fixtures or by invoking isolated train-only preprocessing/candidate helpers using unchanged approved training inputs and protocol. With those fixed, changed validation/calibration inputs must not alter fitted preprocessing, baseline state, or logistic parameters. These tests do not create a public bypass around the admission gate.

### Test-only logistic reproduction

For synthetic verification only, reconstruct the binary logistic probability from the frozen transformed row using the standard sigmoid `1 / (1 + exp(-(intercept + Σ(coef_j * x_j))))`, respecting the stored class ordering (scikit-learn's binary decision score maps to `classes_[1]`). Compare this numeric result to the original scikit-learn candidate output using a declared test tolerance. Reconstruct a selected prevalence baseline separately from its stored constant probability. This is an internal test operation, not a public estimator-application, runtime inference, `SafetyAssessment`, calibration, reliability-scoring, policy, or deployment API.

## Artifact and safe export

```python
@dataclass(frozen=True)
class SafetyEstimatorArtifact:
    artifact_version: str
    scope: TrainingScope
    family: Literal["prevalence_baseline", "l2_logistic"]
    feature_schema: FrozenFeatureSchema
    preprocessing: FrozenPreprocessingState
    dataset_reference: TrainingDatasetReference
    signal_run_reference: SignalRunReference
    # fixed candidate configuration, finite selected state, software versions,
    # selection evidence, lifecycle and safe limitations are mandatory.

    def to_dict(self) -> dict[str, object]: ...  # detached allowlisted data

def validate_artifact(
    payload: Mapping[str, object],
    expected_compatibility: ArtifactCompatibility,
    origin_verifier: ArtifactOriginVerifier,
) -> SafetyEstimatorArtifact: ...
```

The exported payload is canonical, versioned JSON-compatible data, not a pickled Python/sklearn object. Load checks exact scope, registry compatibility, the Feature 003 manifest-bound dataset-build identity (`dataset_id`, manifest reference and independently verified digest, protocol ID/version, builder version and complete admitted inventory), Feature 004 references, method/schema/preprocessing versions, finite coefficient/intercept shape or baseline probability, format digest and independently authorized origin. Feature 003/004 do not define a separate `dataset_version` field. A digest alone does not prove origin. The host controls any storage and receipt; a valid in-memory artifact/export does not establish durable persistence. Serialization excludes patient/group/row identifiers, correctness targets, raw predictors, protected data and restricted verification evidence. Training metrics and validation selection metrics are labeled separately; aggregate support/metrics are included only under the protocol's disclosure policy, otherwise a safe suppression reason is recorded. The artifact always says `uncalibrated` and `non_deployable`; it is not a `SafetyAssessment` or complete safety package.

## Exceptions and compatibility

Use privacy-safe typed errors (`TrainingInputError`, `TrainingVerificationError`, `TrainingCompatibilityError`, `TrainingArtifactError`) with stable codes and no raw patient/row/category values. Routine infeasibility uses `TrainingOutcome` rather than an uncaught numerical exception. Fail closed on incompatible exact classifier version/label, adapter/preprocessing identity, dataset/protocol/manifest, Feature 004 method/reference state, feature order or artifact version. No silent migration or sharing across contributors.
