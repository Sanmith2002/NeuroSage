# Feature Specification: Patient-Grouped Safety Dataset Builder for Safira

**Feature Branch**: `feature-03/Safety-Dataset-Builder` (existing checkout; no branch created)

**Created**: 2026-10-17

**Status**: Clarified — ready for technical planning

**Input**: Build reproducible supervised research datasets from validated Feature 002 predictions and supporting evidence, joined to independently verified binary outcomes, with patient grouping, independent supervision and protected final evaluation data.

## Clarifications

### Session 2026-10-17

- Q: Which ground-truth verification and independence-evidence approach should Feature 003 require? → A: An authorized integration checks each outcome against source evidence bound to the exact patient, assessment, label, and target; records documented primary-model data lineage; and excludes cases whose evidence cannot be verified.
- Q: Who should establish and verify that differently named patient records across sources refer to the same person? → A: An authorized linkage service or data custodian supplies a versioned, opaque equivalence and overlap mapping with its source and scope evidence; the builder checks it and leaves unresolved links uncombined.
- Q: What should the approved research protocol control for four-way patient splits, adequacy checks, and the protected final-test lifecycle? → A: A versioned protocol defines either patient assignments or a deterministic grouped allocation, scope-specific adequacy criteria, applicable site/time/stratification constraints, allowed protected-test checks, and release/reuse conditions. The builder enforces it, uses no universal ratios or minima, and reports infeasibility.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build Traceable Correctness Examples (Priority: P1)

As a researcher, I want each eligible primary prediction joined to its verified outcome so I can prepare a correctness target for later safety-estimator training and trace every example to its exact classifier and assessment.

**Why this priority**: Incorrect outcome linkage or incompatible target meanings would invalidate supervision before any safety model is trained.

**Independent Test**: Supply synthetic admitted live and precomputed records, exact registrations, target definitions and verification evidence. Check joins and correctness targets against known outcomes, including separate classifiers predicting overlapping labels.

**Acceptance Scenarios**:

1. **Given** a valid prediction and a verified outcome for the same patient, assessment, label and target definition, **when** an example is built, **then** its correctness target is 1 if the registered predicted class equals the verified outcome and 0 otherwise, using the declared outcome coding without a new score cutoff.
2. **Given** standalone binary, multi-label and multi-model inputs, **when** examples are built, **then** each retains its exact contributor model ID, version and label; two contributors predicting the same label remain separate examples.
3. **Given** missing, unverified, ambiguously linked or conflicting outcomes, **when** records are joined, **then** affected records receive explicit exclusion reasons and no correctness target is fabricated. A patient need not have ground truth for every label to retain independently eligible examples.
4. **Given** a prediction with missing or invalid optional evidence, **when** its required supervision and provenance checks pass, **then** the example preserves the evidence states and values genuinely available; its suitability is evaluated under the declared dataset eligibility rules.
5. **Given** a primary probability or non-probability score, **when** an example is built, **then** its value, meaning and original class mapping are preserved. Predictor confidence is never substituted for correctness or reliability.

---

### User Story 2 - Keep Every Patient in One Partition (Priority: P1)

As a researcher, I want all records belonging to one patient to share a partition so that visits, labels, contributors and overlapping cohort entries cannot leak the same person across development and evaluation data.

**Why this priority**: A row-level split can overstate performance even when individual records and outcomes are valid.

**Independent Test**: Use synthetic patients with several visits, labels, model versions and cohort aliases. Validate a declared partition configuration and check that all linked records share one patient assignment across related dataset views.

**Acceptance Scenarios**:

1. **Given** one patient with multiple assessments, collection occurrences, labels and contributing classifiers, **when** partitions are assigned, **then** every retained record for that patient belongs to exactly one of training, validation, calibration or final test.
2. **Given** verified source aliases identifying the same patient in overlapping cohorts, **when** the population is assembled, **then** the aliases resolve to the same grouping identity before partitioning; a local identifier without its source namespace cannot establish a cross-source match.
3. **Given** duplicate copies of the same prediction observation, **when** the population is validated, **then** the duplicate does not become an additional supervised example or an independent patient. Conflicting copies cannot silently replace one another.
4. **Given** existing protected patient assignments or site/time isolation requirements, **when** a proposed build conflicts with them, **then** the build reports the conflict and cannot claim compliant partitions by splitting a patient or moving protected records. Missing, partial, stale, conflicting or unverifiable assignment history remains unknown; a manifest's self-declared completeness is insufficient for a cross-version protection claim.
5. **Given** missing or conflicting patient linkage evidence, **when** overlap cannot be resolved, **then** the unresolved scope is explicitly ineligible for a compliant combined dataset; the builder does not assume that unknown overlap means disjoint patients.

---

### User Story 3 - Protect Independent Supervision and Final Testing (Priority: P1)

As a researcher, I want dataset eligibility and partition roles established before fitting or selecting anything so that later training can use independent supervision and leave the final test population untouched.

**Why this priority**: Patient grouping alone does not establish independence from primary-model development, nor prevent leakage through transformations or inspection of final outcomes.

**Independent Test**: Supply synthetic source-development histories, transformation histories and frozen split assignments. Reject disallowed overlaps, outcome-derived predictor inputs and use of protected test data for development, while permitting only the integrity checks authorized by the evaluation protocol.

**Acceptance Scenarios**:

1. **Given** evidence that a proposed safety-supervision cohort overlaps disallowed primary-classifier training, tuning or calibration data, **when** eligibility is checked, **then** the affected scope is excluded under the independence protocol. Missing provenance cannot be treated as proof of independence.
2. **Given** all four partition roles, **when** a dataset is prepared for later fitting, **then** patient assignments precede any safety-workflow fitting of imputation, scaling, feature selection or reference transforms; only the declared training population is authorized for those fitting operations.
3. **Given** a protected final test partition, **when** training, model selection, threshold selection, calibration or ordinary development reporting is requested, **then** final-test observations and outcomes are unavailable for that purpose. The ordinary `DatasetBuildResult`, its serialization and development-facing APIs contain no protected rows, outcomes or correctness targets. Any transfer to the authorized custodian occurs through a separate explicit protected-artifact handoff; the partition is not silently reshuffled or reused as development data.
4. **Given** ground truth or evidence obtained after the prediction's applicable observation window, **when** predictor material is declared, **then** outcome and future information remain supervision/audit material and are not admitted as prediction-time evidence without compatible, documented timing.
5. **Given** serialized prediction values or provenance claims without trustworthy admission lineage, **when** dataset input is checked, **then** constructing a record-shaped object, repeating an assurance string or supplying a digest alone does not establish eligibility.

---

### User Story 4 - Reproduce and Audit a Dataset Version (Priority: P2)

As a researcher, I want an immutable dataset definition and a controlled manifest so that another researcher can reproduce its membership, targets, partitions and exclusions using the same approved inputs.

**Why this priority**: Reproducibility makes leakage checks, later training compatibility and changes to supervision reviewable.

**Independent Test**: Rebuild a synthetic version with equivalent inputs in a different arrival order, compare memberships and targets, inspect its lineage, and confirm that changed sources or corrected outcomes cannot silently rewrite an accepted version.

**Acceptance Scenarios**:

1. **Given** unchanged accepted inputs, linkage and verification evidence, protocol and split configuration, **when** a build is repeated, **then** targets and patient assignments are identical regardless of input arrival order, and all material inputs can be identified from its manifest.
2. **Given** a changed classifier version, target definition, verified outcome, eligibility rule or partition configuration, **when** a new build is accepted, **then** the change is represented by a new dataset version and does not mutate an earlier version or its protected assignments.
3. **Given** an exclusion or readiness failure, **when** an authorized researcher audits it, **then** the reason and applicable source/protocol lineage are available in controlled records, while ordinary logs and reports expose no identifying patient data or sensitive row content.

---

### User Story 5 - Recognize Insufficient or Imbalanced Data (Priority: P2)

As a researcher, I want the builder to distinguish a valid collection of observations from data adequate for the intended study so that limited cohorts cannot create unjustified training or evaluation claims.

**Why this priority**: Large row counts may contain few independent patients, and disease prevalence does not describe the balance of correct and incorrect predictions.

**Independent Test**: Use synthetic cohorts with too few patients, rare outcomes, only correct predictions, only incorrect predictions, missing labels and incompatible partition constraints. Evaluate them against explicitly declared adequacy criteria without manufacturing observations.

**Acceptance Scenarios**:

1. **Given** inadequate distinct patients, unsupported correctness classes or infeasible partitions under the approved protocol, **when** adequacy is assessed, **then** the builder reports `INSUFFICIENT_EVIDENCE` and reasons for the affected model/version/label scope; it does not invent samples or claim reliable evaluation.
2. **Given** missing mandatory protocol or verification information, **when** a build is requested, **then** it reports `NOT_READY` for that scope and does not assume default research thresholds, ratios or verification success.
3. **Given** uneven label coverage or absent modalities, **when** other required checks pass, **then** absence alone does not imply a negative disease outcome, a measured zero, an all-label requirement or complete evidence. Counts and eligibility are reported for the declared scope without leaking protected test outcomes.

### Edge Cases

- The same local patient reference is used by two sources for different people; one person has several source references, visits or cohort memberships.
- A related build introduces a patient already assigned to protected test data, or incompatible older manifests claim two partitions for one patient.
- A label name is shared across classifiers but has a different target definition, horizon or outcome coding; display-name equality is insufficient for an outcome join.
- Several verified outcome assertions disagree, or a later correction changes an outcome previously used to derive correctness; no latest-value or majority rule is inferred.
- The outcome exists for a different visit, prediction window or label; a missing outcome is not a negative outcome.
- A component is incomplete for a declared contributor set, or a contributor lacks required supervision; any retained narrower dataset must explicitly describe its scope and exclusions rather than claim completeness.
- A precomputed record has checked output provenance but no raw-input verification; this limitation remains explicit and does not automatically establish or negate supervision eligibility.
- A record's primary class conflicts with its exact registered mapping, or a probability/score changes after provenance verification.
- Duplicate exports, repeated visits and distinct stochastic outputs are different concepts. Replaying an observation cannot inflate sample size; a supplied repeated-output evidence list is not automatically a set of supervised rows.
- A source transform or feature selection was fitted on all proposed safety partitions, an explanation incorporates future information, or outcome/provenance fields are proposed as predictor features.
- A patient has every visit after a proposed time boundary but another source places an earlier visit in training; patient isolation takes precedence over producing a superficially balanced split.
- Very few patients, a single correctness class, scarce positive outcomes or incompatible site/time constraints prevent the requested protocol from being satisfied. No seed search using final-test results is permitted.
- Reproducing a dataset cannot recover the original verification evidence, input version or patient linkage; a familiar file name, seed or manifest digest does not prove reproducibility or provenance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The builder MUST accept only validated, source-qualified Feature 002 predictions with trustworthy admission lineage tied to the exact accepted prediction/evidence content and applicable patient, assessment and occurrence. It MUST preserve live versus checked-precomputed assurance and its limits. An assurance field, Boolean, class instance or caller-supplied digest alone MUST NOT establish provenance. It MUST NOT require an original live binding for eligible precomputed records.
- **FR-002**: Each prediction MUST be checked for compatibility with the exact immutable Feature 001 model/version/label, binary outcome meanings, class mapping, continuous-output semantics and applicable adapter/preprocessing identity. No latest-version fallback, classifier substitution or silent repair of an incompatible predicted class is permitted.
- **FR-003**: Supervision MUST join the exact patient, assessment, label and explicit target definition/version, including applicable observation window or prediction horizon and outcome coding. Each prediction occurrence MUST remain distinguishable. Target compatibility MUST be explicitly declared for the registered contributor; shared label text or a component version alone is insufficient.
- **FR-004**: An authorized research integration MUST execute a check against authoritative source evidence binding each outcome to the exact outcome content, patient, assessment, label and target definition/version. The verification record MUST identify the responsible authority, method, evidence reference, applicable version/timing and limitations. The integration MUST record documented primary-model data lineage sufficient to assess independence under the approved protocol. A source assertion, matching identifier or caller-supplied verification flag alone MUST NOT count as executed verification. Failed, absent, stale under the declared protocol, conflicting or unverifiable outcome or independence evidence MUST NOT produce eligible supervision; the record MUST receive a safe exclusion reason. The feature MUST NOT promise universal verification.
- **FR-005**: Dataset eligibility MUST include documented independence from the primary classifier's training, tuning, calibration and other development data under an explicitly approved research protocol, with cohort/patient/source and processing provenance sufficient to assess overlap. Unknown independence MUST remain unknown and prevent an independence-qualified dataset claim; source-reported scope metadata alone is not proof.
- **FR-006**: The builder MUST reject or explicitly exclude missing, non-binary, uncertain, incompatible, unverified or conflicting outcomes as supervised examples. It MUST retain a safe reason and MUST NOT invent clinical truth, resolve disagreement by an undeclared rule, or label an unobserved outcome negative.
- **FR-007**: For an eligible join, the correctness target MUST encode 1 when the registered primary predicted class equals the verified outcome and 0 when it differs, using the declared mapping of the two outcome meanings. It MUST NOT derive correctness from a new probability boundary, predictor confidence, an evidence value or a Safira reliability score. The target encoding and its interpretation MUST be recorded.
- **FR-008**: Eligible standalone binary classifiers, multi-label classifiers and arbitrary independent component contributors MUST use the same supervision rules. Every example MUST retain exact model ID, version, label and contributor/component provenance where supplied. Source-specific dataset views MUST remain distinguishable; combining records MUST NOT imply safety-package transfer, merge overlapping labels or decide a future safety-estimator architecture.
- **FR-009**: Primary probabilities and non-probability scores MUST preserve their original values and meanings, scale, class mapping and calibration declarations. Supporting evidence MUST preserve Feature 002's `available`, `unsupported`, `missing`, `unavailable` and `invalid` states, reasons, interpretation, source association and relevant explanation/calibration, modality, repeat and cohort-scope meanings. No optional evidence may be fabricated or silently upgraded.
- **FR-010**: A versioned eligibility definition MUST state its target/population scope, permitted source provenance, observation timing, required versus optional evidence and exclusion rules. Incomplete optional evidence MUST NOT be a blanket rejection unless that declared study scope requires it. Missing modalities or labels MUST NOT imply all-label exclusion. Any retained narrower scope MUST be explicit.
- **FR-011**: Before partitioning, every included record MUST resolve to a stable opaque patient grouping identity across relevant visits, labels, occurrences, sources, cohorts, models and versions. Source identifiers MUST be namespace-qualified. Cross-source equivalence and cohort-overlap mappings MUST be supplied by an authorized linkage service or data custodian as a versioned, opaque declaration with source and scope evidence. The builder MUST check mapping integrity, scope, conflicts and applicable lineage; it MUST NOT perform clinical identity matching. Unresolved or conflicting linkage MUST NOT be assumed disjoint, and affected records MUST remain outside any combined dataset claim that depends on that equivalence.
- **FR-012**: The builder MUST support distinct training, validation, calibration and protected final-test roles under an approved, versioned research protocol. The protocol MUST specify either supplied patient assignments or a deterministic patient-grouped allocation, including its exact seed and algorithm/configuration, the required site/time isolation and any permitted stratification constraints, and applicable final-test integrity checks, access/release and reuse conditions. For deterministic allocation, the builder MUST use exactly the approved seed/configuration and MUST NOT try alternative seeds; it MUST report infeasibility even if another seed could produce a favorable allocation. All related records for one patient MUST occupy exactly one role across source-specific views. The builder MUST enforce the protocol, report infeasibility, and MUST NOT invent universal split percentages or minima.
- **FR-013**: The builder MUST detect exact duplicate observations, conflicting copies and known cohort overlap before partition publication. An exact duplicate MUST NOT increase example or patient counts; conflicting copies MUST NOT silently overwrite accepted data. Genuine repeated observations MAY remain only with their distinct assessment/occurrence provenance and declared eligibility, and MUST stay grouped by patient.
- **FR-014**: Related builds and contributor views MUST check existing patient-assignment and protected-test manifests for conflicts. An explicitly injected trusted research integration MUST verify each prior manifest's origin, source/version, requested and declared scope, completeness evidence, and relevant protected-test membership against independently controlled custodian history. A manifest's self-asserted completeness, identifier, or digest alone MUST NOT establish verified history coverage. Missing, partial, stale, conflicting or unverifiable history MUST remain unknown and MUST NOT support a cross-version protection claim; if the protocol requires verified history, the build MUST be `NOT_READY`. A new seed, new contributor, renamed source or new dataset version MUST NOT silently move a protected patient into development. Unresolved assignment conflicts or unsatisfied grouping constraints MUST prevent compliant dataset publication.
- **FR-015**: Patient partition membership MUST be fixed before any future safety-workflow fitting of reference transforms, imputation, scaling, feature selection or estimators. Dataset outputs MUST identify each role's permitted use and retain declared transformation provenance. Known fitting on held-out safety partitions MUST be detected as leakage; the builder MUST NOT fit or repair those transformations itself.
- **FR-016**: Ground truth, correctness targets, verification decisions and other outcome-derived audit information MUST remain distinguishable from candidate predictor material. Evidence timing and source history MUST be checked against its declared availability at prediction. Post-outcome or otherwise prohibited information MUST NOT be admitted as prediction-time material merely because it is present in an input record.
- **FR-017**: Protected final-test observations, outcomes and correctness targets MUST be isolated from training, model/feature selection, primary or safety operating-point selection and calibration, including use to choose split seeds or eligibility rules. Assembly of supervised final-test examples and their targets may occur only within the protected dataset-construction boundary; it does not authorize development inspection of those values. The ordinary `DatasetBuildResult`, all ordinary serialization forms and development-facing APIs MUST NOT expose protected final-test rows, outcomes or correctness targets. Transfer of the row-bearing protected artifact MUST use a separate explicit handoff to the protocol-authorized custodian; this boundary MUST NOT add a storage service. Before the versioned protocol's release condition is met, only its expressly allowed integrity/eligibility checks and structural summaries may occur. Feature 003 MUST NOT execute final evaluation or assert that later models or policies are frozen.
- **FR-018**: Adequacy checks MUST apply the versioned protocol's justified, scope-specific criteria, distinguish independent patient counts from example counts, and assess the declared model/version/label scope, outcome coverage, correctness-class support and partition feasibility. Counts for development partitions and protected summaries MUST respect FR-017 and the protocol's access rules. No universal minimum sample count, balancing target or split ratio may be invented.
- **FR-019**: A missing required protocol or verification prerequisite MUST produce `NOT_READY`; data that fails declared adequacy criteria MUST produce `INSUFFICIENT_EVIDENCE` with applicable scope and reasons. Diagnostic artifacts MAY describe the failure but MUST NOT be presented as datasets ready for the intended training/evaluation protocol. Neither status establishes clinical safety.
- **FR-020**: The builder MUST NOT fabricate patients, outcomes or samples, duplicate observations to improve class balance, or weaken grouping/protection rules to satisfy requested counts. It MUST NOT silently rebalance, resample, discard classes or change partitions when constraints are infeasible. Any future sampling or weighting procedure requires its own specified, justified protocol.
- **FR-021**: Each dataset version MUST have a reproducible manifest identifying input content/versions and admission lineage, exact registrations and target definitions, supervision/independence evidence references, patient-linkage version, eligibility and exclusion rules, partition configuration/seed where applicable, materialized patient assignments, protected-test lineage, transformation declarations and builder/protocol versions. Equivalent accepted populations under the same configuration MUST produce identical targets and assignments regardless of arrival order; a seed alone is insufficient.
- **FR-022**: Controlled audit records MUST trace every accepted example and excluded candidate to its contributing prediction, outcome verification, grouping identity and partition or exclusion reason. Accepted dataset contents and manifests MUST be immutable or defensively copied. Corrected truth or changed inputs/rules MUST require a new traceable version without changing prior accepted artifacts or bypassing FR-014.
- **FR-023**: Dataset artifacts MUST use only necessary opaque references and permitted content under explicit handling/eligibility declarations. Identifying patient values, raw observations, sensitive evidence and patient-level trace references MUST NOT appear in ordinary logs, committed fixtures or ordinary generated reports. Controlled linkage and row manifests remain sensitive; they MUST NOT be automatically published or committed. Routine errors MUST use safe categories and non-identifying scope/count information.
- **FR-024**: Existing Feature 001, Feature 002, adapter, context and assessment contracts MUST remain unchanged. Ground-truth definitions, patient equivalence and research protocols MUST be additional dataset inputs linked to existing records, rather than invented existing fields. The builder MUST NOT perform original-classifier inference or require re-collection solely to prepare a dataset.
- **FR-025**: The feature MUST be limited to dataset construction, validation and partition/provenance preparation. It MUST NOT compute any of the six safety dimensions, construct learned safety features, train safety estimators, perform Safira reliability calibration, select policy, generate reliability scores or TRUST/CAUTION/DEFER, make diagnoses, modify primary-model pipelines, or create new clinical verification guarantees.
- **FR-026**: Automated acceptance verification MUST use synthetic fixtures to cover all three classifier configurations, admitted live and precomputed sources, correct/incorrect target derivation, both primary score kinds, missing labels/modalities, all five evidence states, provenance failures, ambiguous truth and patient linkage, repeats/duplicates, cohort overlap, cross-visit/contributor grouping, protected-test misuse, transformation leakage, imbalance/limited data, deterministic rebuilds, immutability and privacy. Existing Feature 001/002 and adapter/context/assessment regression behavior MUST be verified during later implementation.

### Key Entities *(include if feature involves data)*

- **Prediction observation**: An admitted Feature 002 primary prediction and evidence for one patient/assessment/occurrence and exact model/version/label, with its distinct provenance assurance.
- **Target definition**: A versioned research outcome meaning, binary outcome coding and applicable temporal/population scope, explicitly associated with each eligible registered label.
- **Verified outcome assertion**: A binary reference outcome for the exact patient/assessment/label/target, with authoritative source lineage, timing, executed verification evidence and any correction/conflict history.
- **Supervised correctness example**: An eligible prediction/outcome join with correctness target, preserved primary semantics and optional evidence states, linked to one patient group and one partition.
- **Patient grouping and overlap declaration**: Authorized equivalence between namespace-qualified source references and one opaque patient group, with cohort/linkage provenance and explicit unresolved cases.
- **Eligibility and evaluation protocol**: Versioned independence, timing, required-evidence, allocation, permitted-use and adequacy requirements; includes the protected-test lifecycle without choosing a safety-model design.
- **Dataset version and partition manifest**: Stable dataset membership, patient assignments, source-specific scope/views, split configuration and lineage sufficient to reproduce a build and detect incompatible prior assignments.
- **Exclusion and readiness record**: Controlled reasons for unjoined/ineligible observations or a scope that is not ready/insufficient; ordinary reports retain only permitted aggregate information.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In synthetic eligible cases across all three classifier configurations and both collection modes, 100% of joined examples retain their exact contributor and target meanings and have the expected correctness target; zero unverified, mislinked or incompatible outcomes become supervised examples (FR-001–008).
- **SC-002**: Across synthetic repeated visits, overlapping cohorts, labels, occurrences and contributors, patient intersection between every pair of the four partitions is empty. Exact duplicate observations increase neither retained example counts nor independent patient counts, and all conflicting patient assignments are detected. Missing, partial or unverifiable prior history never produces verified cross-version protection (FR-011–014).
- **SC-003**: Every declared leakage probe involving source-development overlap, future/outcome-derived predictor material, held-out transform fitting or protected-test development use receives an explicit rejection/exclusion or non-ready outcome; zero contaminated scopes are reported compliant (FR-005, FR-014–017).
- **SC-004**: Repeated builds of the same approved synthetic population/configuration, including reordered inputs, reproduce 100% of correctness targets and patient assignments using exactly the protocol's seed/configuration. An infeasible declared allocation is reported even when an unapproved alternative seed would be favorable. Every accepted example and excluded candidate has controlled lineage/reason coverage; mutations or revisions do not change earlier accepted versions (FR-021–022).
- **SC-005**: All five evidence states, both primary score kinds, missing-label and missing-modality cases retain their declared semantics in synthetic datasets. No absence is converted into a negative disease outcome, fabricated measurement, correctness target or safety result (FR-006–010).
- **SC-006**: Every synthetic inadequate/imbalanced or infeasible population produces the expected scope-specific readiness result under the declared protocol, with zero fabricated samples and no unapproved changes to grouping, thresholds or partitions (FR-018–020).
- **SC-007**: Synthetic privacy probes find zero identifying values, sensitive observations or patient-level trace references in ordinary diagnostics and reports. Protected final-test rows, outcomes and correctness targets are absent from the complete ordinary result and serialization surfaces; transfer occurs only through the separate custodian-controlled handoff. Compatibility regression checks pass without changing existing contracts (FR-017, FR-023–024, FR-026).
- **SC-008**: Dataset construction performs zero original-classifier inference, safety-signal computation, safety-model fitting, reliability calibration, policy selection or safety-assessment operations in automated synthetic verification (FR-024–026).

## Assumptions

- Safira Constitution v3.0.0 governs the feature, especially patient isolation, independent supervision, evidence-derived targets, protected final testing, privacy and research claim limits.
- The repository already implements Feature 001 exact registrations and Feature 002 records, collection and provenance boundaries. Inspection of their public contracts and source shows no dataset builder, verified-ground-truth contract, cross-cohort patient-equivalence contract or comprehensive versioned target definition. Those are new dataset inputs; a registered label's display text is not a substitute.
- Existing primary class mappings are authoritative. No real classifier threshold, clinical reference standard, source field or patient linkage can be inferred from synthetic fixtures or the PD handoff.
- Source owners and authorized research integrations must supply permitted data and the evidence needed to verify association, target meanings and appropriately independent supervision. The builder can check evidence under an approved protocol; it cannot establish arbitrary clinical truth or unknown cohort disjointness by inspecting numeric predictions.
- Four partition roles are required for the intended later workflow. An approved protocol must specify their allocations and adequacy; no default percentage, minimum patient count or class-balancing algorithm is assumed here.
- Dataset construction remains independent of disease, algorithm, label naming, contributor count and safety-estimator design. Actual clinical/research validation of a later safety package is outside this feature.

## Scope and Contract Boundaries

Feature 003 produces eligible, traceable supervised research data and protected partition definitions for later work. It preserves accepted primary/evidence values and does not turn arbitrary evidence structures into learned numerical safety features. The six constitutional dimensions remain future consumers; missing evidence is not a seventh signal. No model training, clinical ground-truth adjudication service, automatic patient identity discovery, universal cryptographic verification, component fusion, external source onboarding, primary-pipeline rewrite, or evaluation execution is introduced by this specification.

Required inputs and permitted access to protected data must be defined in the approved protocol and validated before implementation. Passing software tests will demonstrate these dataset safeguards under the supplied protocol; it will not establish clinical validity or a deployable safety package. Safira remains a research prototype, not a clinically validated medical device.
