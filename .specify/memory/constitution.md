<!--
Sync Impact Report
- Version: unversioned scaffold -> 1.0.0 (initial project constitution).
- Modified principles: five template placeholders -> Principles I-XIII below.
- Added sections: Additional Constraints; Development Workflow.
- Removed sections: none; template placeholders and example comments were replaced.
- Follow-up TODOs: none.
This review comment is temporary and is to be removed before committing the constitution.
-->
# Safira Constitution

## Core Principles

### I. Post-Hoc Reliability, Not Disease Prediction
Safira MUST assess the reliability of an existing clinical classifier's prediction. It MUST
NOT present its reliability score or safety decision as a disease prediction, diagnosis, or
treatment recommendation. Predictor confidence alone MUST NOT establish that a prediction
is safe to trust. This separation prevents a high disease probability from being mistaken
for evidence of correctness.

### II. Patient-Label Assessment and Patient-Level Isolation
One patient-label pair MUST be the fundamental assessment unit. Safira MUST preserve a
separate, traceable assessment for each label and MUST NOT obscure a material label-level
DEFER through any overall patient summary. All labels and repeated records from one
patient MUST remain in the same data partition during splitting. This avoids both
misleading aggregation and patient-level leakage.

### III. Preserve the Existing Adapter and Assessment Contracts
New work MUST reuse the standardized `ModelAdapter`, `AdapterCapabilities`,
`SafetyContext`, and `SafetyAssessment` contracts where they fit. Changes to these
contracts or existing functionality MUST have a documented technical or safety reason,
compatibility impact, and tests. Unnecessary rewrites are prohibited because they risk
breaking the model-agnostic boundary already present in Safira.

### IV. Exactly Six Safety Dimensions
Safira MUST organize safety evidence into these six dimensions: data sufficiency,
distribution conformity/out-of-distribution (OOD), prediction uncertainty, modality
agreement, domain familiarity, and explanation stability. Implementations MUST NOT
silently add a seventh dimension. Clinical harm severity, if used, belongs to an
explicitly specified policy or evaluation protocol rather than an invented signal.
These dimensions define evidence families, not six mandatory numeric outputs.

### V. Automatic, Model-Specific Safety Packages
For each registered primary classifier and exact model version, Safira MUST provide an
automatic setup path that trains and freezes a linked safety package when eligible
labelled safety data and validation evidence exist. The package MUST record the
classifier, adapter, preprocessing, label scope, evidence definitions, calibration,
decision policy, and provenance needed to check compatibility. A package MUST NOT be
assumed to transfer to another classifier or incompatible version. If setup cannot
meet the evidence requirements, it MUST stop with an explicit restricted state rather
than manufacture a trained package.

### VI. Independent Data, Provenance, and Untouched Test Evidence
Safety training MUST use appropriately independent labelled data with reliable outcome,
cohort, timing, and processing provenance. Data partitioning MUST occur by patient before
fitting reference transforms or safety models; site or time isolation MUST be added when
the evaluation claim requires it. Fitting, model selection, calibration, policy selection,
and final testing MUST be separated by a documented protocol. The final test partition
MUST remain untouched until the model and policy are frozen. These rules prevent leakage
and inflated safety claims.

### VII. Explicit Signal Availability
Every safety signal MUST distinguish supported and measured evidence from unsupported,
missing, and failed extraction. Unsupported or unavailable signals MUST be reported as
unavailable and MUST NOT be silently replaced by fabricated values such as zero. A
model-specific policy MUST define which evidence is required for each outcome. This keeps
absence of evidence from appearing to be reassuring evidence.

### VIII. Evidence-Derived Targets and Operating Points
The model-correctness or other reliability target MUST be defined in advance against
appropriate labelled outcomes and its meaning MUST be stated. Its validity, estimator
calibration, and TRUST/CAUTION/DEFER operating points MUST be assessed or selected using
appropriate held-out evidence under the documented split protocol. Thresholds and gates
MUST NOT be arbitrary constants or derived from the untouched final test set. A
reliability score MUST identify what quantity it estimates and the evidence supporting
that interpretation.

### IX. Safe Abstention and Readiness
Safira MUST issue TRUST only within the model, label, population, data, and policy scope
supported by sufficient validation and required runtime evidence. When that evidence is
insufficient or compatibility fails, it MUST report NOT_READY, INSUFFICIENT_EVIDENCE, or
an appropriately restricted outcome with reasons; it MUST NOT claim clinical safety.
CAUTION and DEFER MUST follow a validated policy, not an ad hoc score cutoff. Runtime
assessment MUST NOT require a new patient's ground-truth label.

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

Safira targets Python 3.11 or later and remains model-agnostic through its adapter
boundary. Specifications MUST define the label and outcome semantics, eligible data,
reference population, mandatory and optional signals, missing-evidence behavior,
package compatibility rules, and evaluation scope before implementing a training or
runtime decision path. Algorithms, targets, minimum sample sizes, and operating points
MUST be justified by the protocol and evidence rather than hard-coded in this
constitution. Model identifiers, package versions, and provenance MUST remain traceable
without retaining identifiable patient content in logs or committed artifacts.

## Development Workflow

Feature work MUST start with a specification, continue through a plan and dependency-
ordered tasks, and end with implementation and verification against acceptance criteria.
Reviewers MUST confirm patient-level isolation, held-out calibration and policy evidence,
untouched final testing, capability-aware signal handling, safe failure behavior,
model-version compatibility, privacy, and accurate research claims where applicable.
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

**Version**: 1.0.0 | **Ratified**: 2026-10-15 | **Last Amended**: 2026-10-15
