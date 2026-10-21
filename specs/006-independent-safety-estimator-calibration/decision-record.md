# Feature 006 Approved Decision Record

**Feature**: Independent Safety Estimator Calibration
**Branch**: `feature-06/Independent-calibration`
**Recorded**: 2026-10-21
**Status**: Decisions A–G approved by the research owner; reflected normatively in `spec.md`.

This record captures the seven approved Feature 006 V1 methodology decisions. It supplements, and does not rewrite, the pre-specification `methodology-review.md` or `architecture-feasibility.md`. Their historical statements that choices were pending approval refer to their original review stage.

## Decision A — Fixed calibration method

- For a selected Feature 005 `l2_logistic` artifact, privately reconstruct the frozen linear predictor `z` using the artifact's exact stored feature order, training-fitted preprocessing, coefficients and intercept. Fit only `q = sigmoid(a + b*z)` against independently verified correctness targets.
- For a selected `prevalence_baseline` artifact, require `0 < p0 < 1` and fit only `q = sigmoid(logit(p0) + a)`. Preserve constant-output semantics and state that this mapping adds no individualized discrimination.
- Do not use isotonic regression, compare calibrators on the same fitting evidence, fall back to another algorithm, or emit successful identity-only calibration.

## Decision B — Repeated-patient estimand

- Give each prediction occurrence equal weight in the V1 calibration objective. State that this is occurrence-weighted and gives greater influence to patients with more occurrences.
- Evaluate independent evidence adequacy using unique verified patient groups; repeated visits are not independent patients.
- Patient/group identifiers are restricted metadata, never predictors or ordinary artifact content. Defer clustered uncertainty estimates pending a separately justified method.

## Decision C — Evidence adequacy

Require complete independently authorized Feature 003/004 evidence; exact classifier/version/label matching; protocol-approved independent patient-group and class support; both correctness target classes; adequate identifiable score variation for logistic slope fitting; and finite valid predictor/target representations.

Do not invent universal minima, class ratios or score-variation cutoffs. Missing approval yields `NOT_READY`; approved but inadequate evidence yields `INSUFFICIENT_EVIDENCE`; missing required compatible signals yield `UNAVAILABLE_REQUIRED_EVIDENCE`; malformed, incompatible and numerical failures remain distinguishable.

## Decision D — Numerical fitting

- Approve fixed unpenalized logistic maximum-likelihood fitting using the approved existing scikit-learn `1.7.1` dependency and its supported `lbfgs` solver.
- A versioned protocol must declare solver configuration, tolerance, maximum iterations, convergence and separation criteria, deterministic expectations and any allowed safeguards before calibration outcomes are examined.
- Reject separation, rank deficiency, nonconvergence and non-finite estimates according to those approved criteria. Do not silently regularize, clip, retry with changed settings or switch methods. Use stable calculations.

## Decision E — Non-positive slope

A non-positive fitted slope for the varying-score logistic mapping is a non-success. Do not reverse score ordering, clip/force the slope positive, or substitute intercept-only fitting. The approved protocol must define treatment of numerically ambiguous slopes without an invented tolerance. The constant baseline mapping has no estimated slope and is exempt from this check.

## Decision F — Artifact and reporting

- Success status: `CALIBRATOR_FITTED_UNEVALUATED`.
- Produce a deeply immutable, exact-scope artifact bound to the selected Feature 005 artifact and schema/preprocessing; independently verified Feature 003 calibration evidence; Feature 004 methods/run/fitted references; and approved protocol/version/configuration.
- Use allowlisted safe serialization; do not use unsafe pickle/joblib artifact deserialization. Mark the result non-deployable, not independently evaluated and not clinically validated.
- Restrict ordinary reports to approved fitting/convergence and privacy-safe lifecycle/adequacy metadata. Do not emit default in-sample Brier, log loss, ECE, reliability diagrams, or calibration-performance claims. Do not expose a public per-patient application or `SafetyAssessment` API.

## Decision G — Independent trust and evidence lifecycle

Feature 006 independently verifies exact Feature 001 registration, Feature 002 admission lineage, Feature 003 manifest/calibration targets/inventory, Feature 004 calibration rows and references, and Feature 005 frozen artifact compatibility and origin. A constructed object or matching digest alone is insufficient. An approved host-controlled origin verifier/receipt is required for newly created in-memory and loaded Feature 005 artifacts. The core cannot authenticate arbitrary malicious Python controlling the trusted host.

Only Feature 003 calibration rows affect fitting. Feature 005 train and validation are not reused; validation has already been spent selecting the base estimator. Feature 003 calibration is spent after calibration fitting. Protected final-test remains inaccessible. Future independent evaluation and policy selection require separately authorized evidence. No durable-storage guarantee is made without an authorized custodian that verifies it.

## Traceability

| Decision | Normative specification coverage |
|---|---|
| A | FR-007–FR-010; US2; SC-002, SC-005 |
| B | FR-011–FR-012; US2; SC-003 |
| C | FR-012–FR-015; US1–US2; SC-001, SC-005 |
| D | FR-008, FR-014–FR-015, FR-024; US2; SC-002, SC-005–SC-006 |
| E | FR-013–FR-015; US2; SC-005 |
| F | FR-018–FR-025; US3; SC-007–SC-008 |
| G | FR-002–FR-006, FR-016–FR-017, FR-022–FR-026; US1–US3; SC-001, SC-004, SC-006–SC-009 |

## Limitations retained

These approvals define a research-software method, not scientific validation in Safira's target setting. The trusted host must provide independent verification integrations; no production ledger, artifact custodian, durable persistence guarantee, independent evaluation set, policy-selection evidence or protected-test access is configured. Protocol owners must approve exact adequacy and numerical settings before a fit can be ready.
