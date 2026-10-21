# Feature 008 Research Decisions

## Decisions

### D1 — Execution boundary

**Decision**: Restrict V1 to internal synthetic-fixture research/testing execution. Do not accept real patient data, provide a public/general runtime API, or create a `SafetyAssessment` projection.  
**Rationale**: Feature 007 policies are `SELECTED_UNEVALUATED`; the Constitution requires validated packages for actual patient-label assessment. The research owner approved only a synthetic-only internal simulation.  
**Alternatives considered**: A host-attested synthetic API was not approved; applying the policy to real data is deferred until independent policy evaluation and separate authorization.

### D2 — Result contract

**Decision**: Use a private immutable result marked `SYNTHETIC_TEST_ONLY` and `SELECTED_UNEVALUATED`; include exact scope, a non-reversible association fingerprint, safe status/reason, artifact digests, and explicit lifecycle limitations. Do not include the calibrated numeric score or raw identifiers.  
**Rationale**: The existing mutable `SafetyAssessment` lacks exact provenance and lifecycle constraints and can serialize patient-associated fields. It is not a fit for this internal synthetic path; no existing contract is changed.  
**Alternatives considered**: Reusing `SafetyAssessment` by adding metadata would not make its lifecycle immutable or prevent public patient-level output.

### D3 — TRUST/CAUTION/DEFER semantics

**Decision**: Reuse the single Feature 007 frozen cutoff and its exact comparison rule. For synthetic fixtures only, map a valid calibrated score satisfying the rule to `TRUST` and one that fails the stored comparison to `CAUTION`. Shared verification, authorization, origin, or cross-scope failures reject atomically without a result. After complete admission, a required runtime measurement that is unavailable, invalid, incompatible, or not ready yields `DEFER`; optional missingness follows only the frozen Feature 005 behavior. No additional thresholds.  
**Rationale**: This preserves already approved Feature 007 selection semantics without changing its methodology. The status result is a software-behavior simulation, not policy-performance evidence.

### D4 — Frozen transformations

**Decision**: Reconstruct only the approved Feature 004 reference from verified original training evidence, compare its exact identity/digest to frozen artifact bindings, and apply it to the query without admitting the query to fitting. Reuse the private Feature 007 Feature 005/006 score transformation only behind a new single-record adapter.  
**Rationale**: Feature 004 does not export portable fitted state; Feature 007's signal-row builder expects a Feature 003 validation dataset. Its score math is reusable, but its row-admission workflow is not a runtime API.  
**Alternatives considered**: Refitting on the query, accepting caller-supplied signal rows, or calling `SignalExtractor.build_feature_set` on runtime data violates frozen-state boundaries.

### D5 — Trust and provenance

**Decision**: Inject the trusted host; require executed Feature 002 admission, exact registry identity, complete original Feature 003/004 provenance, exact origin checks for estimator/calibrator/policy, and approval of the policy protocol whose digest matches the policy artifact. Use existing typed artifact-origin checks; never accept caller claims or fabricate receipts.  
**Rationale**: Core Python cannot authenticate an untrusted host. No production evidence ledger or artifact custodian exists in the repository.

### D6 — Explanation availability

**Decision**: Report only the existing Feature 004 explanation-applicability result and verified Feature 002 explanation availability when the approved protocol uses them. Do not copy or fabricate explanation content in the private result.  
**Rationale**: `AdapterCapabilities` establishes possible support, while the admitted record establishes per-prediction availability; these are different facts.

## Technical Findings

- `SignalExtractor.extract_record` independently admits one prediction and calculates configured stateless signals. Its reference-based results are `NOT_READY` without a Feature 003 dataset.
- `SignalExtractor.build_feature_set` admits a Feature 003 dataset and fits reference state from its training partition; it must not receive runtime observations.
- `FittedStateReference` contains identity and digest metadata, not portable reference vectors or domain vocabularies.
- `safira.policy.references.reconstruct_original_references` rebuilds exact Feature 004 states from original training examples and checks their digests.
- `safira.policy.signals.build_policy_signal_rows` privately builds rows from a Feature 003 validation dataset and `CorrectnessExample`; directly adapting it would import dataset/target semantics into the runtime entry point.
- `safira.policy.scoring.reconstruct_calibrated_scores` reconstructs the frozen Feature 005 transform and applies the Feature 006 mapping but accepts internal signal rows and returns per-row scores. Those values must remain ephemeral inside the new private service.
- `SelectivePolicyArtifact` binds the exact scope, estimator/calibrator digests, protocol digest, cutoff and comparison configuration, and records that selection remains unevaluated/non-deployable.
- No central roadmap or Feature 001–005 closure record files were found; their specifications, decision records, implementation contexts where present, and current code remain the source references. Feature 006 and Feature 007 have explicit closure records.

## Unresolved External Dependencies

- An independently controlled host that can execute prediction, dataset/reference, estimator, calibrator, and policy-origin verification.
- Access to the authorized original training evidence and Feature 004 protocol/manifest required for exact reference reconstruction.
- Production persistence, custody, patient-data services, independent policy-evaluation evidence, and deployment infrastructure are absent and outside this feature.
