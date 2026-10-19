# Implementation Context: Feature 004

Reusable handoff summary for future implementation. Read this with [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), and [signals-python.md](contracts/signals-python.md).

## Existing contracts to preserve

- **Feature 001**: `ModelRegistry.get_metadata(model_id, model_version)` is exact-version metadata-only lookup. `resolve_usable` requires a live classifier-adapter binding. Feature 004 must not invoke primary inference or modify registry identity.
- **Feature 002**: `PredictionRecord` is immutable/source-qualified by exact `(model_id, model_version, label_id)`, has `PrimaryOutput` semantics and `EvidenceItem` values with `available`, `unsupported`, `missing`, `unavailable`, `invalid` states and interpretation/provenance. Use these records as evidence source; do not reconstruct states from `SafetyContext.evidence_availability()`.
- **Feature 003**: `DatasetBuildResult.development` exposes train, validation and calibration; protected rows and complete manifest are controlled separately. `CorrectnessExample` also contains outcome, correctness, `patient_group_ref`, partition role and verification references. These are supervision/partition controls, never signal predictors. `manifest_reference`/receipt alone is not evidence of durable storage.
- **Legacy contracts**: Do not modify `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment`; do not add methods or fields to Features 001–003.
- **Implemented repository state**: `src/safira/signals/` contains immutable records/configuration, trusted-input validation, stateless signal calculations, reference fitting/cross-fitting, public orchestration and typed errors. Synthetic coverage lives in `tests/test_signals_*.py` and `tests/signals_fixtures.py`. The package uses the standard library and existing repository dependencies; no new runtime dependency was added.

## Implemented modules

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

## Dependency order and current behavior

1. Immutable records/config/state enums and typed errors are implemented.
2. Exact Feature 001/002 validation and explicitly injected `SignalInputVerifier` checks guard record and complete Feature 003 dataset admission.
3. Stateless coverage, entropy, modality JSD, repeated-output variance and explanation applicability are implemented with explicit signal states.
4. Reference compatibility, deterministic patient-grouped folds, whole-group exclusion, kNN and domain familiarity are implemented. Final state uses training-only evidence; validation/calibration apply frozen state.
5. `build_feature_set` validates all embedded predictions before fitting or publishing, and keeps predictor rows separate from outcome, correctness, patient grouping and partition metadata.
6. Protocol-scoped cohort adequacy is configured by exact `SignalSourceKey` with `CohortAdequacyCriteria`. Unique groups count once; optional correctness-class support is computed only when declared. Within-source patient groups with conflicting correctness are excluded from all class counts. Missing criteria is `not_ready`; unmet declared support is `insufficient_evidence`.
7. `apply_protected` sends reference-only scope to an injected custodian and returns a matching receipt/status only; protected rows/values are never part of ordinary objects.
8. Synthetic tests cover method behavior, privacy, leakage, provenance and Feature 001–003 regressions. Run focused and full pytest suites after further changes.

## Non-negotiable invariants

- Every result/state is exact model ID, model version and label ID; component ID never substitutes; no cross-contributor transfer/fusion.
- Only admitted Feature 002 values and verified Feature 003 development inputs. Validation checks the exact complete input, every row's content/source/association/partition, and invokes the record verifier for each embedded prediction before signals, cohort support, feature sets or fitted states are published. The injected provider must consult independently controlled evidence. The trusted host selects the provider; the library cannot authenticate a malicious implementation injected by code that controls the Python process. No repository application entrypoint provides untrusted provider selection. An echoed typed check, fingerprint, authority string or evidence reference is not proof independent of the configured provider.
- Fit only on Feature 003 training predictor evidence. Patient-grouped cross-fitting uses one protocol seed/config, excludes the scored group from its fold reference and never searches another seed. A verified change in patient grouping may change fold assignments and cross-fitted scores; merely renaming opaque group references without changing evidence/configuration must not change the final full-training fitted reference. If infeasible, report `insufficient_evidence`.
- Final state is fitted only on eligible training predictor values. Validation/calibration apply frozen state only. Protected test is apply-only under the custodian boundary after state freeze; no ordinary API has protected values.
- Never place outcomes, correctness, target labels, patient/assessment/group IDs, partition assignments or protected membership in predictor values. Row-alignment keys remain separate and opaque.
- Feature 002 evidence states remain unchanged; Feature 004 signal states distinguish unsupported, missing, unavailable, invalid, insufficient evidence and not ready. `insufficient_evidence` means valid evidence lacks method/protocol-required support; `not_ready` means a required compatible reference, approval, provenance or verification prerequisite is absent or unready. Never fabricate zero.
- Deep immutability/detached serialization; safe error codes only. No patient data in routine logs.
- No estimator training, reliability calibration, policy/threshold selection, assessment, clinical diagnosis or safety claims.

## Open implementation dependencies and limits

- A trusted host must provide `SignalInputVerifier` checks for live/precomputed record admission and exact Feature 003 build/manifest scope. No real verifier is configured. If a future application allows untrusted callers to select providers, selection must move behind trusted host configuration; this in-process library cannot authenticate malicious provider code.
- A host custodian must provide the optional protected apply integration and control artifact access/persistence. No real integration is configured; the library checks receipt/request consistency but a receipt alone does not authenticate execution or establish durability. Deployment must authorize and independently govern the custodian integration.
- Research owner must approve vector metric/`k`, any representation transform, log bases/aggregation, privacy-safe category mapping, fold count/seed and per-method adequacy in a versioned protocol.
- Evidence may be absent or semantically incompatible. Such signals remain non-values; synthetic tests do not establish scientific utility.
