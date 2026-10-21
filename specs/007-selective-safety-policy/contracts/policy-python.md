# Feature 007 Python Contract

This contract specifies a cohort-level research workflow. It does not expose per-patient scoring, runtime policy application, or safety assessment.

## Public boundary

```python
class PolicyInputVerifier(Protocol):
    def verify_prediction(self, record: PredictionRecord) -> SignalInputCheck: ...
    def verify_dataset(self, dataset: DatasetBuildResult,
                       reference: PolicyEvidenceReference) -> PolicyDatasetAdmission: ...
    def verify_ground_truth(self, example: CorrectnessExample,
                            prediction: PredictionRecord,
                            scope: PolicyScope) -> PolicyOutcomeAdmission: ...
    def verify_patient_disjointness(self, policy_reference: PolicyEvidenceReference,
                                    prior_history: tuple[PriorAssignmentManifest, ...],
                                    protected_scope: object) -> PatientDisjointnessCheck: ...
    def verify_artifact_origin(self, kind: str, digest: str,
                               scope: tuple[str, str, str], version: str) -> ArtifactOriginCheck: ...


class PolicySelectionService:
    def __init__(self, registry, protocol: PolicySelectionProtocol,
                 input_verifier: PolicyInputVerifier): ...

    def select(self, *, policy_dataset: DatasetBuildResult,
               original_training_dataset: DatasetBuildResult,
               original_signal_protocol: SignalProtocol,
               estimator_artifacts: Mapping[PolicyScope, SafetyEstimatorArtifact],
               calibrator_artifacts: Mapping[PolicyScope, CalibratorArtifact],
               prior_history: tuple[PriorAssignmentManifest, ...]) -> tuple[PolicySelectionOutcome, ...]: ...
```

The verifier is explicitly injected and selected by trusted host construction, never caller input. `verify_prediction` returns the existing Feature 004 `SignalInputCheck` contract after the trusted provider checks Feature 002 admission; the core recomputes fingerprints, matches exact inventories, executions and scopes, and validates returned checks against submitted inputs. A caller-supplied Boolean, digest, prebuilt check or `accepted` field is not proof. If no trusted provider or required independent evidence is configured, the service returns `NOT_READY` or raises a stable typed shared verification exception before any scope outcome is published.

The exact host evidence contract must bind:

- each submitted Feature 002 prediction content, contributor, version, label, association and executed admission lineage;
- each Feature 003 policy dataset, source inventory, exact manifest/digest/protocol/builder, validation partition, correctness target/ground-truth binding and one chosen index assessment per patient/scope;
- trusted cross-source linkage and authoritative history completeness/scope, including protected membership sufficient to establish non-overlap without disclosing protected rows;
- each Feature 005 and Feature 006 artifact's exact canonical content, scope, original provenance, version, independently checked origin and compatibility;
- original Feature 003 training records and Feature 004 run/method/reference provenance used for deterministic state reconstruction;
- exact one-to-one alignment of each new policy prediction and its Feature 004 signal row.

The check objects are evidence references/statuses, not autonomous cryptographic proofs. The trusted integration documents its actual source checks. Core library guarantees do not cover malicious code controlling the trusted process.

## Private score reconstruction

Private helpers in `safira.policy.references` and `safira.policy.scoring` MUST:

1. Re-admit the original training dataset and all embedded Feature 002 predictions; use only its verified `train` predictor evidence to reconstruct Feature 004 fitted references.
2. Recompute the original method/version/configuration and fitted-state digest for every state required by the Feature 005 artifact. Require exact equality to the frozen Feature 005 and Feature 006 provenance; never synthesize a matching reference or refit on policy records.
3. Independently admit the new Feature 003 policy dataset, every embedded Feature 002 prediction, every correctness target, and its exact validation inventory. Use its validation partition only.
4. For each admitted validation prediction, derive a Feature 004 row internally using the exact original `SignalProtocol`: reuse the existing record-level extraction semantics for stateless dimensions, then replace reference-method `not_ready` values only by applying the verified reconstructed original reference state. Derive the policy row key from the new policy dataset identity and prediction fingerprint, and verify one-to-one alignment to the admitted prediction.
5. Do not accept a caller-provided `SignalFeatureSet` or `SignalFeatureRecord` as proof of policy features. The service creates the rows from the verified predictions, original approved method configuration, and exact reference states; any optional supplied cache must be discarded or independently recomputed before use.
6. Reconstruct the exact Feature 005 typed schema/preprocessing from its allowlisted versioned artifact fields, verify dimensions/order/feature semantics, and apply only frozen transforms. Do not fit imputation, scaling, category maps, schema, estimator or references from policy rows.
7. Reconstruct only the Feature 005 estimator output required by the Feature 006 mapping. Apply the exact mapping encoded in the verified `CalibratorArtifact`: logistic `q = sigmoid(intercept + slope*z)` when that artifact's mapping type is logistic; use its frozen constant probability for a baseline mapping. Reject unsupported/malformed mapping versions and nonfinite values.
8. Keep `q`, targets, patient group keys, and row keys in a local ephemeral selection batch; discard it after aggregate cutoff selection.

This is new Feature 007-private behavior because existing Feature 005/006 public APIs intentionally expose no inference operation and Feature 004 does not export reusable fitted state. It must not change or monkeypatch upstream modules. It may use only exact documented artifact schemas and compatibility checks; internal helper reuse must be version-pinned and tested against source workflows. It must not invoke Feature 006 calibration fitting on new evidence.

## Selection contract

The frozen `PolicySelectionProtocol` supplies the risk ceiling, exact scope, one-index-assessment-per-patient rule, eligibility/support criteria, candidate generator, score comparison/equality, tie handling, status mapping, and disclosure. No default numerical threshold/minimum is introduced.

For each candidate cutoff, compute empirical patient risk only if selected patient count is positive, and coverage only if eligible patient count is positive. A candidate is feasible only if its empirical risk is within the approved ceiling and all protocol support criteria are met. Choose maximum coverage. Tied cutoffs follow the protocol's frozen deterministic rule. Empty selection has undefined risk and never yields success. A constant score permits only all-or-none selection; nonempty TRUST is allowed only if it satisfies the same empirical rule and support.

The selection result and artifact carry aggregate selection statistics only when disclosure is approved. They do not contain individual q values or statuses. A successful artifact state is `SELECTED_UNEVALUATED`, `selection_evidence_spent=true`, `independent_evaluation_complete=false`, `protected_test_accessed=false`, `deployable=false`, and `clinical_validity_established=false`.

## Data and errors

- Policy records and artifacts are recursively immutable/defensively detached. `to_dict()` returns detached allowlisted JSON values.
- Safe typed failures contain controlled reason codes, never raw values, IDs, patient content, source exception text or optimizer details.
- Exact scope incompatibility, missing trusted evidence, new evidence overlap, changed artifact/reference digest, inventory mismatch, invalid target, unsupported state, and unavailable original training state fail closed before selection.
- Scope-local insufficient support or no feasible nonempty selection returns a non-success `PolicySelectionOutcome` with no artifact.
- No output asserts durable storage, authenticated origin from a digest alone, clinical efficacy, a risk guarantee, independent evaluation, or deployment readiness.

## Proposed package modules

| Path | Responsibility |
|---|---|
| `src/safira/policy/records.py` | Immutable protocol, policy scope, provenance references, outcome, summary and artifact. |
| `src/safira/policy/verification.py` | Injected host verification orchestration; complete exact inventory and cross-dataset disjointness. |
| `src/safira/policy/references.py` | Private original Feature 004 training-only state reconstruction and exact digest check. |
| `src/safira/policy/signals.py` | Private per-prediction Feature 004 row derivation from admitted Feature 002 records and verified original reference states. |
| `src/safira/policy/scoring.py` | Private frozen Feature 005 transformation, estimator output and Feature 006 mapping application. |
| `src/safira/policy/selection.py` | Deterministic empirical threshold candidates, risk/coverage calculation and selection. |
| `src/safira/policy/artifacts.py` | Canonical digest, allowlisted serialization and compatibility checks. |
| `src/safira/policy/service.py` | Atomic shared admission, per-scope selection/freeze and safe outcomes. |
| `src/safira/policy/exceptions.py` | Stable privacy-safe public failures. |

## Test contract

Tests use synthetic data only. Cover positive exact-scope scoring, estimator/calibrator mapping reproduction, reference digest recreation, patient-group index selection, no evidence leakage, risk/coverage/cutoff equality/ties, empty sets, constant scores, exact scope isolation, mismatched/stale/forged verifier evidence, prior-history incompleteness, artifact provenance separation, mutation/serialization/privacy, no protected access, no public inference method, and unchanged Features 001–006 regressions. Test that new policy data cannot alter original reference, estimator, preprocessing or calibration state.
