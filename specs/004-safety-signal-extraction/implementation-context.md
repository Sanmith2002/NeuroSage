# Implementation Context: Feature 004

Reusable handoff summary for future implementation. Read this with [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), and [signals-python.md](contracts/signals-python.md).

## Existing contracts to preserve

- **Feature 001**: `ModelRegistry.get_metadata(model_id, model_version)` is exact-version metadata-only lookup. `resolve_usable` requires a live classifier-adapter binding. Feature 004 must not invoke primary inference or modify registry identity.
- **Feature 002**: `PredictionRecord` is immutable/source-qualified by exact `(model_id, model_version, label_id)`, has `PrimaryOutput` semantics and `EvidenceItem` values with `available`, `unsupported`, `missing`, `unavailable`, `invalid` states and interpretation/provenance. Use these records as evidence source; do not reconstruct states from `SafetyContext.evidence_availability()`.
- **Feature 003**: `DatasetBuildResult.development` exposes train, validation and calibration; protected rows and complete manifest are controlled separately. `CorrectnessExample` also contains outcome, correctness, `patient_group_ref`, partition role and verification references. These are supervision/partition controls, never signal predictors. `manifest_reference`/receipt alone is not evidence of durable storage.
- **Legacy contracts**: Do not modify `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment`; do not add methods or fields to Features 001–003.
- **Repository state**: `src/safira/signals/base.py` currently has no implementation; `tests/` contains collection/dataset/registry tests but no signal tests. `pyproject.toml` declares no runtime dependencies.

## Proposed modules

```text
src/safira/signals/base.py       protocols, six dimension names, states
src/safira/signals/records.py    immutable configs, results, states, row keys/manifests
src/safira/signals/validation.py exact registry/evidence/dataset checks and leakage guards
src/safira/signals/stateless.py  coverage profile, binary entropy, modality JSD, explanation metadata
src/safira/signals/reference.py  deterministic folds, kNN/domain fit, cross-fit and compatible apply
src/safira/signals/service.py    public extraction/build orchestration, verifier and custodian boundaries
src/safira/signals/exceptions.py typed privacy-safe errors
```

No DB, new service, numerical library or mutable global verifier. Prefer standard-library math/hashlib and an O(N·d) distance scan for the modest research prototype.

## Method behavior

| Dimension | V1 path | State |
|---|---|---|
| Data sufficiency | Evidence prerequisite state profile; separate exact-scope cohort-support summary | Stateless profile; cohort summary not a predictor |
| OOD | k-th nearest distance in compatible registered representation | Training reference; exact metric and `k` in approved protocol |
| Uncertainty | Bernoulli entropy for registered binary probability; repeated variance optional only with verified repeat semantics | Entropy stateless; no non-probability conversion |
| Modality agreement | Pairwise JSD of semantically comparable same-contributor modality probabilities | Stateless; never compare component classifiers |
| Domain familiarity | `seen`/`unseen` against declared allowed category vocabulary | Training reference; category identifiers remain privacy-controlled |
| Explanation reliability | Explanation metadata/target/output-space/calibration applicability only | No generic numeric V1 reliability score |

Candidate methods are not validated for a clinical population. No thresholds or universal sample minima.

## Dependency order for implementation

1. Immutable records/config/state enums and typed errors; validate deep copying and serialization.
2. Exact Feature 001/002 input validation plus explicit `SignalInputVerifier` for record admission and Feature 003 dataset verification. A caller-constructed frozen value, assertion, status or digest alone is insufficient.
3. Test-first stateless methods and state mapping, one method at a time.
4. Reference schema/compatibility validation, deterministic patient-group fold assignment and feasibility behavior.
5. kNN and domain-vocabulary fitting, whole-group exclusion cross-fit, final training-only state and frozen validation/calibration apply.
6. Feature 003 row alignment and predictor/supervision separation; immutable feature sets/run manifests.
7. Custodian apply-only boundary that sees only frozen-state/scope references in ordinary process and returns safe receipt/status, never protected rows or transformed values.
8. Synthetic end-to-end/privacy/leakage/immutability tests, Feature 001–003 regression, then full pytest suite.

## Non-negotiable invariants

- Every result/state is exact model ID, model version and label ID; component ID never substitutes; no cross-contributor transfer/fusion.
- Only admitted Feature 002 values and verified Feature 003 development inputs. The actual trusted integration must check source evidence independently; never accept a caller Boolean/digest as proof.
- Fit only on Feature 003 training predictor evidence. Patient-grouped cross-fitting uses one protocol seed/config, excludes the scored group from its fold reference and never searches another seed. If infeasible, report `insufficient_evidence`.
- Final state is fitted only on eligible training predictor values. Validation/calibration apply frozen state only. Protected test is apply-only under the custodian boundary after state freeze; no ordinary API has protected values.
- Never place outcomes, correctness, target labels, patient/assessment/group IDs, partition assignments or protected membership in predictor values. Row-alignment keys remain separate and opaque.
- Feature 002 evidence states remain unchanged; Feature 004 signal states distinguish unsupported, missing, unavailable, invalid, insufficient evidence and not ready. Never fabricate zero.
- Deep immutability/detached serialization; safe error codes only. No patient data in routine logs.
- No estimator training, reliability calibration, policy/threshold selection, assessment, clinical diagnosis or safety claims.

## Open implementation dependencies and limits

- A host must provide `SignalInputVerifier` checks for live/precomputed record admission and exact Feature 003 build/manifest scope. No real verifier is configured in the repository.
- A host custodian must provide the optional protected apply integration and control its artifact access/persistence. No real integration is configured; a receipt alone does not establish durability.
- Research owner must approve vector metric/`k`, any representation transform, log bases/aggregation, privacy-safe category mapping, fold count/seed and per-method adequacy in a versioned protocol.
- Evidence may be absent or semantically incompatible. Such signals remain non-values; synthetic tests do not establish scientific utility.
