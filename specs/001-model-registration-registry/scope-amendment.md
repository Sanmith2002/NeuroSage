# Feature 001 Scope Amendment — 2026-10-17

**Status**: Documentation prepared for review; application code and tests unchanged.

## Authority and source review

The user explicitly approved both standalone supervised single-label binary and
supervised multi-label classifiers, plus multiple independently registered classifiers
contributing predictions to one component-level output. This overrides earlier
multi-label-only scope restrictions.

Reviewed the completed registry definitions, operations, identity boundary, storage,
synthetic tests and manual demo against the feature artifacts and the earlier Safira
handoff at `C:/Users/User/.codex/.chatgpt-projects/g-p-6a7fbe9115fc8191af1d408c2020c60d/SAFIRA_HANDOFF.md`.
That earlier handoff supports patient-label assessment and exact model-specific safety
packages. Subsequently reviewed the user-supplied
`C:/Users/User/Downloads/PD Copathology Handoff.md` (dated 2026-10-16).
The handoff is project evidence, not an instruction to expand this amendment. Its
reported results, test counts, hashes and external repository artifacts have not been
independently reproduced or inspected here.

## Exact constitutional amendments

Constitution **2.0.0 → 3.0.0**, retaining ratification 2026-10-15 and setting amendment
date 2026-10-17. Governance requires MAJOR for a principle redefinition: mandatory
multi-label eligibility is redefined, although old multi-label records remain compatible.

| Clause | Amendment |
|---|---|
| II, renamed Classifier-Scoped Label Assessment and Patient-Level Isolation | Both eligible classifier forms; classifier cardinality distinct from component label count; exact contributor provenance, overlapping labels kept distinct; patient-label assessment and patient-level splitting preserved. |
| V, Automatic, Model-Specific Safety Packages | Applies to each eligible classifier/version; component composition cannot transfer or combine package compatibility implicitly. |
| Additional Constraints | Both classifier forms with binary outcomes per label; regression, unsupervised and reinforcement learning remain excluded. |
| Development Workflow | Review both forms and classifier/component cardinality and provenance. |
| Sync Impact Report and footer | Record approval, reason, migration impact, synchronized artifacts and handoff review status. |

Principles I, III, IV and VI-XIII retain their substantive requirements, including exactly
six safety dimensions, privacy, held-out evidence, readiness, automated verification,
existing contracts, and research-prototype claims. No training algorithm is selected.

## Feature artifact amendments

| Artifact | Exact scope change |
|---|---|
| `spec.md` | Amend FR-001 eligibility; retain FR-002-FR-014 protections; add FR-015 exact independent contributor resolution. Amend US1.1 and independent test, US3.3 and cardinality edge cases; add US2.7. Broaden SC-001 and add SC-007. Correct assumptions and boundaries. |
| `data-model.md` | Exactly one label under the new binary task token; at least two under the unchanged multi-label token. Describe source-qualified consumer references without a new stored component entity. |
| `contracts/registry-python.md` | Specify both tokens/count rules, existing typed errors and consumer behavior. Align documented `attach` signature with actual required keyword-only candidate `definition`; no API change. |
| `plan.md` | Align scope, constitution gate and traceability; identify minimal validator/test changes and preserved architecture. |
| `research.md` | Amend schema decision 5; add decision 7 separating classifier cardinality from component composition. Preserve identity decision 3. |
| `tasks.md` | Preserve completed T001-T023 as baseline history; append unchecked T024-T028 for test-first amendment implementation and regression verification. |
| `quickstart.md` | Distinguish existing baseline support/test evidence from pending amended scope; identify new acceptance cases. |
| `checklists/requirements.md` | Remove obsolete single-label exclusion; distinguish specification quality from unexecuted amended verification. |

## Minimal implementation impact

Current `definitions.py` accepts only `supervised_multi_label_classification` and requires
at least two labels. Amend that validator to also accept
`supervised_single_label_binary_classification` with exactly one label. Update related
scope descriptions in `definitions.py` and `exceptions.py`. Keep existing validation for
each label, continuous probability/score semantics and prediction-to-class mappings.
No hard-only classifier support or per-label multiclass support is added.

Keep SQLite metadata storage, serialized fields, schema version, immutable exact keys,
separate process-local bindings, trusted IdentityProvider and fail-closed checks intact.
Existing multi-label records require no rewrite. Old software cannot be assumed to read
new single-label registrations successfully. Task/cardinality/schema changes to a model
require a new model version.

Multiple contributors use existing `get_metadata` and `resolve_usable` calls. Every
contribution retains `(model_id, model_version, label_id)` and adapter compatibility.
Unavailable contributors fail explicitly; consumers cannot silently omit or substitute
them to claim completeness. The registry neither stores patient predictions nor assembles
runtime component outputs. No component registry, table, new operation, aggregation
algorithm, safety estimator, or dependency is required.

## Required regression evidence (pending)

- Replace only obsolete blanket one-label rejection tests in `test_registry_us1.py` and
  `test_registry_us3.py`; retain zero-label, unknown-task and count-mismatch rejection.
- Extend `test_registry_acceptance.py` for binary and multi-label definitions, both
  continuous-output kinds, all-single-label and mixed contributor sets, overlapping
  source labels, wrong-version/unattached sources and zero patient/safety calls.
- Extend `test_registry_us2.py` and `test_registry_concurrency.py` for single-label and
  mixed catalogs: genuine subprocess restart, missing live bindings, exact reattachment,
  immutable versions and concurrent duplicate protection. Preserve legacy catalog reads.
- Retain privacy, deep immutability, unsupported capability and storage failure tests;
  verify invalid identity evidence, false loader attestation and fingerprint mismatch
  still fail closed. A digest alone still cannot establish arbitrary live-object origin.
- Update and run the manual demo after implementation; run the full pytest suite and
  original adapter/assessment contract tests. Record actual totals then.

## Review outcome

The explicit approved scope is specified and implementation work is bounded in
T024-T028. Amended implementation is **not yet verified**. Review of the supplied PD
handoff confirms the scope amendment. Actual PD onboarding remains subject to the
integration gaps below; these do not justify bypassing registration validation.
No application code or tests were modified or executed for this documentation amendment.


## PD Co-Pathology handoff comparison

| Handoff evidence | Amendment alignment / integration consequence |
|---|---|
| Method: each label has its own binary model (binary relevance). Selected PD-type Random Forest, AD-like elastic-net logistic regression, vascular Random Forest. | Three independently registered single-label binary classifiers; not one three-label classifier. Model architecture is not model identity: the two Random Forests need distinct exact model registrations. Existing multi-label support remains valid for other classifiers. |
| Integration contract: one versioned output record with three calibrated probabilities; shared `model_version` is `pd-copathology-v1.0`. | One component output can reference three exact classifier/version/label contributions. Bundle/schema version alone does not establish contributor artifact or adapter identity. Recover exact per-model evidence from the actual frozen manifest through a trusted loader; do not invent version strings or substitute architecture names for identity. |
| Labels: `pd_type_v1`, `ad_like_v1`, `vascular_v1`, with different proxy definitions and cohort eligibility. | Preserve separate outcome meanings, output selectors and input/preprocessing declarations. Do not rename these proxies into diagnoses or infer identical population eligibility. Existing bounded metadata must not acquire patient records or arbitrary report payloads. |
| Output contract explicitly excludes thresholds and yes/no decisions; method section nevertheless mentions thresholds fitted inside folds. | Unresolved: the handoff does not provide a usable, frozen prediction-to-class mapping for each exported probability. FR-003 and the existing label contract still require one. Obtain the authoritative model-specific mapping, or separately review a future mapping-contract amendment. Do not assume 0.5, infer thresholds from performance tables, reuse the AD-like target-definition cut-off as a classifier decision threshold, or invent TRUST/CAUTION/DEFER cutoffs. |
| Bundle verifies file, feature-list and lock hashes and exact runtime version before prediction, without fallback. | Compatible with fail-closed identity verification, but Safira still needs a trusted IdentityProvider linking each loaded classifier and adapter to its exact checked material and candidate schema. A bundle hash or supplied model name alone is insufficient. No universal serialization or change to ModelAdapter is required. |
| SHAP explains the uncalibrated score, not the calibrated output probability; completeness metadata is also returned. | Preserve those meanings when a later adapter integration is specified. SHAP presence does not establish explanation stability/reliability, and completeness alone does not establish all safety dimensions. Register only capabilities actually implemented; registration measures no safety signals. |
| Component final test was opened once on 2026-10-14; models are calibrated primary predictors, with PPMI-only research-proxy validation. | Primary calibration is not Safira reliability calibration or a validated safety package. Do not assume the already opened primary test can serve as an untouched Safira final test, or that primary development data are independent safety data. A future safety-training protocol must establish independent labelled evidence and a protected final partition. This is outside Feature 001. |
| API/database/frontend, shared IDs, inference transport and downstream value validation remain team decisions; demos must be synthetic. | No component persistence, API, transport, inference execution or fusion policy is added to the registry amendment. Preserve privacy and synthetic-only verification. Handoff claims do not constitute clinical validation. |

### Remaining integration questions

1. Supply authoritative per-model artifact/adapter identity material and trusted-loader
   bindings; the handoff supplies neither complete manifests nor adapters for inspection.
2. Supply the declared prediction-to-class mapping for each exported probability, or
   separately approve a change to that existing contract before onboarding those models.
3. Resolve runtime transport, output assembly, feature plausibility checks, explanation
   consumption and safety-data eligibility in their appropriate future specifications.

The minimal registry implementation remains T024-T028. Its tests must use synthetic,
fully declared mappings; passing those tests does not prove the real PD bundle can yet
be registered or assessed safely.
