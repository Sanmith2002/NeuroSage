# Research and Design Decisions: Feature 004

**Input**: clarified [specification](spec.md), [methodology review](methodology-review.md), Constitution v3.0.0, and completed Feature 001–003 contracts.  
**Decision status**: Candidate V1 methods and scope were explicitly approved during clarification. Study parameters and empirical claims remain protocol/data dependent.

## R1. Separate signal extraction from assessment

**Decision**: Feature 004 emits immutable, traceable signal results and predictor-only feature rows. It does not consume a new patient's ground truth, train a safety estimator, calibrate a reliability score, select a policy, or instantiate `SafetyAssessment`.

**Rationale**: This preserves Constitution principles I, III, VIII and IX and the existing `SafetyContext` and `SafetyAssessment` contracts. Feature 002 primary scores remain primary predictions, never Safira reliability.

**Alternatives considered**: Attach signal values to mutable `SafetyContext` fields; rejected because it would change a legacy contract and lose Feature 002's five-state semantics. Generate TRUST/CAUTION/DEFER from signal values; rejected as Feature 005/later scope.

## R2. Four stateless V1 operations

**Decision**: Use (a) evidence-coverage/validity profile, (b) Bernoulli entropy for registered probability outputs, (c) pairwise Bernoulli Jensen–Shannon divergence for comparable modality probabilities, and (d) explanation metadata/applicability only.

**Definitions**:

- Coverage is a structured mapping from declared prerequisites to preserved evidence states; it is not collapsed to a universal scalar.
- For valid registered `p∈[0,1]`, entropy is `−p log(p) − (1−p) log(1−p)`; log base is explicit and `0 log 0=0`. It describes the output distribution, not empirical correctness.
- For comparable Bernoulli modality distributions `P_i`, `P_j`, `JSD(P_i,P_j)=H((P_i+P_j)/2)−(H(P_i)+H(P_j))/2`. With base-2 logs it is in `[0,1]`. Multi-modality aggregation is a protocol parameter; pairwise outputs are preferred to hide no pair.
- Explanation metadata preserves method, exact target, output space, calibration relation and provenance. No numeric explanation-reliability measure is available in V1.

**Inputs and applicability**: Only Feature 002 `PredictionRecord` plus exact Feature 001 `LabelDefinition`/registration metadata. Entropy applies to probability labels; a non-probability score is never transformed. Modality JSD requires two or more same-contributor/same-label/same-assessment outputs with matching scale, target, calibration interpretation and timing. A multi-model component's independent classifiers do not count as modalities. Explanation evidence may be present while its reliability measurement remains unavailable.

**Alternatives considered**: Use probabilities from component contributors as repeated/ensemble outputs; rejected because Feature 001/002 preserve them as independent classifiers. Use prediction correctness as an uncertainty input; rejected as outcome leakage. Use explanation presence as a reliability value; rejected as unsupported inference.

## R3. Reference-based methods and the safety-training reference population

**Decision**: Candidate V1 reference methods are k-th-nearest-neighbour distance and seen/unseen declared domain-category vocabulary. Their reference population is the independent Feature 003 training partition, not the primary classifier's original training cohort.

**kNN operation**: Given representation `z`, compatible reference vectors `Z={z_j}`, a declared metric `d`, and integer `k`, sort distances `d(z,z_j)` and return the k-th distance (no probability transform, decision cutoff, or class prediction). Use same exact model/version/label, Feature 001 preprocessing identity, Feature 002 representation schema/interpretation, and declared reference cohort scope. V1 design supports a flat finite numeric vector and a named metric; an arbitrary callback is not accepted. Euclidean distance is the initial implementation candidate only when protocol owners justify coordinate scale/metric meaning. No hidden standardization is applied. If normalization is later approved, its parameters are fit only on the permitted training reference and included in state/version.

**Domain operation**: Fit the allowed declared category vocabulary on Feature 003 train and return category membership (`seen`/`unseen`) plus the correct signal state when category evidence is absent/invalid. Do not emit raw category identifiers or support counts in predictor features. Source category definitions, site/time scope and privacy approval are required.

**Alternatives considered**: Mahalanobis distance; deferred because it adds covariance estimation, distributional assumptions, regularization and small-sample stability concerns. MMD; kept as a cohort-level research comparison only, not the per-patient V1 output. Domain classifier; deferred because it adds a second predictive model and validation surface. No generic explanation perturbation measure; deferred because no existing contract guarantees controlled model perturbations.

## R4. Patient-grouped cross-fitting and final reference

**Decision**: Create training-row outputs for reference methods using deterministic patient-grouped cross-fitting. The versioned protocol specifies fold count, a single seed and method version. One deterministic hash assignment is made per opaque patient-group reference; that assignment applies across every visit, label, contributor and related row. For each fold, fit the reference on the remaining Feature 003 training groups and score the held-in groups. The held-in group is fully excluded, preventing self-neighbour and self-category support.

**Final state**: After fold-derived training values are made, fit one final immutable reference on all eligible Feature 003 training predictor evidence. Apply that state to validation/calibration records only. The fit provenance contains fold algorithm/version, fold count, seed, method parameters, source dataset/protocol/manifest references, exact model/version/label, preprocessing/schema, evidence provenance and safe counts. Fold role and patient-group reference are gating/alignment data only, never features.

**Infeasibility**: Each fold must meet the protocol's declared reference support (for kNN, at least `k` compatible reference vectors and any approved group criteria). If a fold is inadequate, return `insufficient_evidence` for that scope. Never split patient groups, use held-out partitions, retry a different seed, or score against the patient's own records as a fallback.

**Alternatives considered**: Leave-one-group-out for every row; rejected as default for potentially large repeated fitting cost, but the same exclusion invariant is retained through grouped folds. Score all training rows against the full training reference; rejected because self-influence can inflate familiarity. Select the best seed; rejected because it makes a favorable partition a selection target.

## R5. Protocol-parameterized methods without arbitrary constants

**Decision**: Each `SignalMethodConfig` is immutable and versioned. The research owner approves method parameters and rationale in a versioned protocol before extraction. Required settings include:

- kNN method: representation ID/schema, preprocessing identity, metric, `k`, cohort scope, and any explicitly approved transform.
- Cross-fitting: fold algorithm/version, fold count and one seed; no retries.
- Entropy/JSD: log base, JSD pair coverage or deterministic aggregation rule; probability/calibration compatibility requirements.
- Domain familiarity: source-qualified category field, category mapping/version, permitted cohort/time scope and disclosure rule.
- Data sufficiency: exact required evidence profile and cohort-level adequacy criteria per exact source key, including unique-patient and any required correctness-class support.

Parameters must not be selected using the protected final-test partition. There are no universal sample minima, class balance cutoffs, distance thresholds or reliability operating points in this feature.

## R6. Availability, error and readiness behavior

**Decision**: Preserve Feature 002's evidence states unchanged and add a distinct signal-level state: `available`, `unsupported`, `missing`, `unavailable`, `invalid`, `insufficient_evidence`, or `not_ready`.

**Meaning**: `unsupported`—capability/method is not supplied; `missing`—expected evidence is absent; `unavailable`—supported evidence could not be obtained; `invalid`—supplied evidence fails structural/semantic validation; `insufficient_evidence`—valid evidence fails the method's protocol-declared support needs; `not_ready`—approval, exact compatible reference, trusted provenance or required integration is not ready. A successful explanation metadata record is explicitly metadata/applicability only; it does not imply an explanation-reliability measurement.

**Decision rule**: Adequacy checks use independent patient groups, exact `(model_id, model_version, label_id)` scope and only protocol-required correctness-class support. Each method declares prerequisites; other scope sizes or class support are not universal gates. Cohort support belongs to restricted metadata, never the predictor feature matrix.

**Alternatives considered**: Collapse all failures to missing; rejected because it loses the difference between unsupported, absent, failed and inadequate. Replace unavailable values with 0; rejected by Constitution VII and method semantics.

## R7. Feature 003 input identity, alignment, and verification boundary

**Decision**: Reference fitting accepts only a ready Feature 003 development result plus a `Feature003DatasetReference` naming exact dataset ID, protocol ID/version and manifest reference (and manifest digest when supplied by the custodian). Signal rows align through run-scoped opaque keys separate from `features`. The partition role is a capability gate only; outcome, correctness, target, patient-group identity and protected membership are never predictor values.

**Trust**: Public dataclasses can be constructed by callers. Therefore, a configured `DatasetInputVerifier` must execute a source-specific check against independently controlled Feature 003 build/manifest evidence. It binds an exact canonical detached development-result fingerprint, readiness, dataset/protocol/manifest identity and partition scope. Caller `ready`, a digest assertion, a receipt reference or row fields alone do not establish trusted provenance. Safira checks returned scope and fails closed if the verifier is absent, mismatched or unavailable. The verifier/custodian is host-provided; the plan does not claim universal origin proof or persistence.

**Alternatives considered**: Trust any instance of `DatasetBuildResult`; rejected because frozen value objects remain caller constructible. Request the full manifest through ordinary Feature 003 results; rejected because Feature 003 deliberately keeps it custodian-controlled.

## R8. Protected-test application boundary

**Decision**: Feature 004 ordinary APIs do not accept or return `ProtectedTestArtifact` rows. An injected `ProtectedSignalApplyHandoff` accepts only the frozen signal-state reference, exact dataset/protocol/manifest references and approved scope; the custodian integration itself accesses protected rows and applies the frozen state. Ordinary Feature 004 receives only a detached safe receipt/status. The integration must reject changed identities and cannot refit, tune, expose transformed values, outcomes or correctness distributions to ordinary callers.

**Limit**: There is no real configured custodian integration and Feature 003 does not promise durable storage simply by returning a reference/receipt. Synthetic tests can verify the contract calls and information boundary only. If an authorized custodian cannot execute and document the apply-only operation, protected transformation is not available.

**Alternatives considered**: Let ordinary code take protected rows and return signal values for review; rejected because this violates the approved isolation boundary. Refit references on protected observations; rejected because it contaminates final evaluation.

## R9. Dependencies and empirical claims

**Decision**: V1 depends only on Python standard-library types, `math`, `hashlib`, and current package interfaces. Flat vector distance is a deterministic O(N·d) reference scan suitable for a modest FYP prototype; a future optimized neighbor index requires measured need and separately verified behavior. No database, service, new third-party package, or mutable global registry is required.

**Validation boundary**: Formula fixtures and synthetic tests establish arithmetic, identity checking, partition controls and privacy behavior. They do not establish that a distance, entropy, disagreement or domain flag predicts primary model error. Empirical validation requires a separate study protocol, independent authorized data and the untouched evaluation process defined in Feature 003.

## References

See the linked primary papers in [methodology-review.md](methodology-review.md), including Sun et al. (2022) on deep nearest-neighbour OOD, Shannon (1948) on entropy, Lin (1991) on entropy-based divergence, Guo et al. (2017) on probability calibration, Gretton et al. (2012) on cohort-level MMD, and Yeh et al. (2019)/Adebayo et al. (2018) on explanation evaluation. These support method provenance, not Safira-specific validity.
