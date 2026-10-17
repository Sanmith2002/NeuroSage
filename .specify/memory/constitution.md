<!--
Sync Impact Report
- Version: 2.0.0 -> 3.0.0 (approved redefinition of classifier eligibility).
- Modified principles:
  - II. Multi-Label Safety Assessment and Patient-Level Isolation ->
    Classifier-Scoped Label Assessment and Patient-Level Isolation.
  - V. Automatic, Model-Specific Safety Packages: both eligible classifier forms;
    component composition does not transfer package compatibility.
- Added sections: none. Removed sections: none.
- Other amended text: Additional Constraints and Development Workflow.
- Reason: user-approved standalone binary and multi-model component support.
- Compatibility: existing multi-label registrations remain valid and unchanged.
  Single-label eligibility requires the focused implementation in amendment tasks
  T024-T028; no storage redesign or adapter/assessment contract change is authorized.
- Synchronized: Feature 001 spec, plan, research, data model, Python contract,
  quickstart, checklist, and appended tasks. Templates retain generic headings.
- PD-specific handoff reviewed; actual contributor identity material and prediction-to-class
  mappings remain integration prerequisites; see Feature 001 scope-amendment.md.
-->
# Safira Constitution

## Core Principles

### I. Post-Hoc Reliability, Not Disease Prediction
Safira MUST assess the reliability of an existing supervised clinical classifier's
prediction. It MUST NOT present its reliability score or safety decision as a disease
prediction, diagnosis, or treatment recommendation. Predictor confidence alone MUST NOT
establish that a prediction is safe to trust. This separation prevents a high disease
probability from being mistaken for evidence of correctness.

### II. Classifier-Scoped Label Assessment and Patient-Level Isolation
Safira MUST support standalone supervised single-label binary primary classifiers and
supervised multi-label primary classifiers with binary outcomes for each label. Label
cardinality MUST be evaluated for each individual classifier. Multiple independently
registered classifiers MAY contribute predictions to one component-level output; that
component's combined label count MUST NOT determine any contributor's task type.
Safira MUST independently assess the reliability of each predicted label for a patient.
One patient-label pair is the
fundamental assessment unit. For each assessable pair, Safira MUST produce a traceable
label-level assessment with an individual reliability score between 0 and 1, an individual
TRUST, CAUTION, or DEFER status, and supporting reasons. These outputs MUST use the
corresponding validated model-specific safety package and available evidence. If the
required evidence or validated package is unavailable, Safira MUST explicitly report a
failure or readiness state and MUST NOT fabricate a score or selective status. Labels
from the same patient MAY receive different scores and statuses. Any optional patient-
level summary MUST retain all label-level outcomes and MUST NOT hide or override a
label-level DEFER.

Each prediction and assessment MUST retain its contributing classifier's exact identity,
version, adapter compatibility, and label identity. If several classifiers predict the
same label, their contributions MUST remain distinguishable; composition MUST NOT
silently merge their predictions or transfer reliability evidence between classifiers.
Any aggregation or fusion policy requires a separate specification and validation.

All labels, observations, and repeated records associated with the same patient MUST
remain in one data partition to prevent leakage. Automatic Model-Specific Safety
Training MUST support both eligible classifier forms and packages that assess each supported
label independently. The feature specification and experimental validation MUST decide
whether this uses separate per-label safety models or a shared label-aware estimator;
this constitution does not prescribe either design.

### III. Preserve the Existing Adapter and Assessment Contracts
New work MUST reuse the standardized `ModelAdapter`, `AdapterCapabilities`,
`SafetyContext`, and `SafetyAssessment` contracts where they fit. Changes to these
contracts or existing functionality MUST have a documented technical or safety reason,
compatibility impact, and tests. Unnecessary rewrites are prohibited because they risk
breaking the model-agnostic boundary already present in Safira.

### IV. Exactly Six Safety Dimensions
Safira MUST organize safety evidence into these six dimensions: data sufficiency,
distribution conformity/out-of-distribution detection (OOD), prediction uncertainty,
modality agreement, domain familiarity, and explanation reliability. Explanation
stability MAY be one measurement approach within explanation reliability; it MUST NOT
silently replace the broader dimension. Implementations MUST NOT silently add a seventh
dimension. Clinical harm severity, if used, belongs to an explicitly specified policy
or evaluation protocol rather than an invented signal.
These dimensions define evidence families, not six mandatory numeric outputs.

### V. Automatic, Model-Specific Safety Packages
For each registered supervised single-label binary or multi-label primary classifier
and exact model version,
Safira MUST provide an automatic setup path that trains and freezes a linked safety
package when eligible labelled data and validation evidence exist. The path MUST cover
these logical responsibilities in order:

1. Register the classifier and identify its exact version.
2. Prepare appropriately independent labelled safety data.
3. Extract safety features automatically according to declared adapter capabilities.
4. Train a model-specific safety estimator.
5. Calibrate it using independent evidence.
6. Select a selective-classification policy from held-out validation evidence.
7. Evaluate the fixed estimator and policy on an independent final test partition.
8. Freeze and version the safety package.
9. Assess new patient-label predictions using that compatible frozen package.

These responsibilities need not be separate software modules. The package MUST record
classifier and adapter identity, preprocessing, label scope, evidence definitions,
calibration, decision policy, validation and final evaluation provenance, and version
compatibility. A package MUST NOT be assumed to transfer to another classifier or
incompatible version. Setup MUST NOT produce a deployable package when essential
training, calibration, or validation requirements are unmet.
Combining predictions in a component MUST NOT make contributors' safety packages
interchangeable or remove their individual compatibility and evidence requirements.

### VI. Independent Data, Provenance, and Untouched Test Evidence
Safety training MUST use appropriately independent labelled data with reliable outcome,
cohort, timing, and processing provenance. Data partitioning MUST occur by patient before
fitting reference transforms or safety models; site or time isolation MUST be added when
the evaluation claim requires it. Fitting, model selection, calibration, policy selection,
and final testing MUST be separated by a documented protocol. The final test partition
MUST remain untouched until the estimator, calibration, and policy are fixed. These rules
prevent leakage and inflated safety claims.

### VII. Explicit Signal Availability
Every safety signal MUST distinguish supported and measured evidence from unsupported,
missing, and failed extraction. Unsupported or unavailable signals MUST be reported as
unavailable and MUST NOT be silently replaced by fabricated values such as zero. The
validated model-specific policy MUST define required and optional evidence for each
outcome. At setup time, insufficient essential training, calibration, or validation
evidence MUST prevent release of a deployable package. At runtime, missing evidence
MUST follow the frozen policy and result in a restricted outcome or readiness state
when required; it MUST NOT trigger invented signal values or policy changes. This keeps
absence of evidence from appearing to be reassuring evidence.

### VIII. Evidence-Derived Targets and Operating Points
The safety-training target MUST be derived from a comparison between each primary
classifier prediction and its verified ground-truth label. Its correctness criterion
and the reliability score's meaning MUST be defined in advance. Safira MUST evaluate
individual label predictions and apply a validated, model-specific selective-
classification policy. Estimator calibration and TRUST/CAUTION/DEFER operating points
MUST be assessed or selected using appropriate held-out evidence under the documented
split protocol. Thresholds and gates MUST NOT be arbitrary constants or derived from
the untouched final test set. Evaluation SHOULD report appropriate selective-
classification metrics, including coverage, selective risk or error, and deferral
behavior, with reasons for any omission.

### IX. Safe Abstention and Readiness
For an assessable patient-label pair, Safira MUST apply the validated model-specific
selective-classification policy. TRUST means the label prediction satisfies its
validated acceptance criteria. CAUTION means it requires additional scrutiny under
that policy. DEFER means Safira abstains from endorsing the label prediction and flags
it for further review. TRUST MUST be limited to the model, label, population, data, and
policy scope supported by sufficient validation and required runtime evidence. None of
the three outcomes may follow classifier confidence alone or an ad hoc cutoff.

NOT_READY and INSUFFICIENT_EVIDENCE are readiness or evidence states, not additional
selective-classification categories. When setup evidence, package compatibility, or
required runtime evidence is insufficient, Safira MUST report one of these states or
an appropriately restricted outcome with reasons, without fabricating a reliability
score or claiming clinical safety. Runtime assessment MUST NOT require a new patient's
ground-truth label.

### X. Privacy and Claim Discipline
Safira MUST protect patient privacy: logs and routine diagnostic output MUST NOT contain
identifiable patient data, restricted datasets MUST NOT be committed, and artifacts MUST
carry only the minimum permitted information. Documentation, reports, and interfaces MUST
NOT make unsupported clinical performance or safety claims. Privacy and restrained claims
are necessary for responsible use of sensitive clinical data and research results.

### XI. Automated Verification and Reproducibility
Every new feature MUST include meaningful automated pytest coverage, clear exception
handling, and a reproducible experiment or deterministic verification path appropriate
to its behavior. Tests MUST cover relevant error, missing-evidence, leakage, and
compatibility cases. Experiments MUST record data and split provenance, configuration,
versions, and evaluation results without exposing restricted data. This makes failures
and claims reviewable.

### XII. Specification-Driven Change
Every new feature MUST proceed through specification, plan, tasks, implementation, and
verification. Each stage MUST identify affected contracts and evidence requirements.
Existing functionality MUST NOT be rewritten without a documented and justified reason.
This workflow keeps changes aligned with Safira's safety contract and preserves working
architecture.

### XIII. Research Prototype Boundary
Safira MUST be described as a research prototype, not a clinically validated medical
device. TRUST, CAUTION, and DEFER are research safety decisions within a validated
experimental scope; they MUST NOT be represented as authorization for autonomous
clinical use. Any broader clinical claim requires separate evidence and review.

## Additional Constraints

Safira targets Python 3.11 or later. Its current research and implementation scope is
supervised classification with standalone single-label binary and multi-label primary
classifiers, each label having binary ground-truth outcomes. It MUST remain model-
agnostic across supervised classifier architectures through its adapter boundary.
Automatic safety training MUST use appropriately labelled data with known, verified
reference outcomes. Safira MUST NOT claim support for unsupervised learning,
reinforcement learning, or regression models within this scope; expansion to any of
those paradigms requires an explicitly approved constitutional amendment.
Specifications MUST define the label and outcome semantics, eligible data,
reference population, mandatory and optional signals, missing-evidence behavior,
package compatibility rules, and evaluation scope before implementing a training or
runtime decision path. Algorithms, targets, minimum sample sizes, and operating points
MUST be justified by the protocol and evidence rather than hard-coded in this
constitution. Model identifiers, package versions, and provenance MUST remain traceable
without retaining identifiable patient content in logs or committed artifacts.

## Development Workflow

Feature work MUST start with a specification, continue through a plan and dependency-
ordered tasks, and end with implementation and verification against acceptance criteria.
Reviewers MUST confirm both eligible classifier forms, classifier-versus-component label
cardinality, source-qualified label-level behavior, patient-level
isolation, held-out calibration and policy evidence, untouched final testing,
capability-aware signal handling, safe failure behavior, model-version compatibility,
privacy, and accurate research claims where applicable.
Verification MUST include pytest and reproducible experimental evidence for the feature's
scope. A missing validation result MUST be recorded as a limitation, not inferred from
passing software tests.

## Governance

This constitution governs future Safira specifications, plans, tasks, implementation,
reviews, and research reporting. Amendments MUST be proposed in the constitution file
with a reason, affected principles, compatibility or migration impact, and a Sync Impact
Report; they take effect after project review and approval. Every feature review MUST
check compliance and document any justified exception before implementation proceeds.
The constitution uses semantic versioning: MAJOR for incompatible principle removals or
redefinitions, MINOR for added principles or materially expanded guidance, and PATCH for
non-semantic clarification. The version and amendment date MUST be updated with each
approved change. Templates and other guidance remain subordinate to this constitution.

**Version**: 3.0.0 | **Ratified**: 2026-10-15 | **Last Amended**: 2026-10-17
