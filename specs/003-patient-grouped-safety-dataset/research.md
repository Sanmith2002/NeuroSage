# Research: Patient-Grouped Safety Dataset Builder

**Date**: 2026-10-17
**Status**: Design decisions resolved from the approved specification and inspected repository.

## Decision 1: Consume Feature 002 records and exact Feature 001 metadata

**Decision**: The builder consumes immutable `safira.collection.PredictionRecord` values and uses `ModelRegistry.get_metadata(model_id, model_version)` to validate exact registered label semantics. It does not invoke `resolve_usable`, attach classifiers, or run primary inference.

**Rationale**: `PredictionRecord` already carries the patient/assessment/occurrence association, exact model/version/label key, mapped `predicted_class`, score meaning and scale, source assurance, and five-state optional evidence. The registry already enforces immutable exact-version label/adapter definitions. Reusing these avoids parallel prediction schemas and makes dataset preparation independent of classifier availability after collection.

**Alternatives considered**:
- Re-collect predictions during dataset build: rejected because it couples supervision preparation to active model bindings, can change source values, and violates Feature 003's no-inference boundary.
- Copy Feature 002 records into a new mutable prediction model: rejected because it duplicates contract behavior and risks losing provenance/evidence semantics.

## Decision 2: Require an explicit trusted research verifier for outcome and independence checks

**Decision**: Inject a verifier instance into each builder. It executes source-specific checks for exact outcome content/association/target scope and documented primary-model data lineage. It returns typed immutable check records bound to the checked subject, source/version, method, timing and scope. A caller-supplied Boolean, identifier match, or digest is not an executed check. Unverifiable, stale, conflicted or insufficiently independent data is excluded or yields `NOT_READY` according to the protocol.

**Rationale**: Feature 001 has no ground-truth contract; Feature 002 validates prediction/source provenance but does not establish outcome truth or training-data independence. The approved C1 decision assigns those checks to an authorized integration that can access the relevant source evidence. The integration boundary is explicit and local to a builder; it introduces no hidden global state or claim of universal verification.

**Alternatives considered**:
- Treat outcome and independence declarations as self-asserted metadata: rejected because it would admit unverified supervision.
- Build a universal clinical adjudication or cryptographic verification service: rejected as unsupported, unnecessarily complex and outside Feature 003.
- Accept unverifiable outcomes as marked examples: rejected because they cannot train an independence-qualified correctness estimator.

## Decision 3: Use exact, versioned target-to-label semantics

**Decision**: Each outcome target definition is versioned and declares positive/negative meanings, scope and timing. A separate compatibility declaration maps the outcome meanings to the exact registered `(model_id, model_version, label_id)` and its binary class meanings. The builder compares the verified outcome to the existing `PredictionRecord.primary.predicted_class`; it never recalculates a class from `primary.value`.

**Rationale**: Feature 001's label mapping is the sole approved prediction-to-class mapping. Research target definitions and source coding are new Feature 003 inputs. Explicit mapping prevents label-name equality or a shared component version from being mistaken for semantic equivalence.

**Alternatives considered**:
- Infer compatibility from matching label IDs or display strings: rejected because labels can share names while referring to different outcomes, populations or horizons.
- Reapply probability thresholds during dataset construction: rejected because thresholds belong to the registered classifier definition and inventing a second cutoff would alter primary semantics.

## Decision 4: Verify patient equivalence from authorized versioned linkage declarations

**Decision**: A linkage service or data custodian supplies versioned opaque patient-equivalence and cohort-overlap declarations, their namespaces, scope and evidence references. An explicitly injected trusted integration checks the declaration's source and applicable scope. Safira validates uniqueness/conflicts and groups records by the supplied opaque group identity; it never performs clinical identity matching. Unresolved links remain unknown and cannot support a combined disjointness claim.

**Rationale**: Feature 002 patient references are opaque and only meaningful within their source. A local `patient_ref` or occurrence is not a cross-system identity. The approved C2 decision establishes who supplies linkage and how the builder must treat unresolved cases.

**Alternatives considered**:
- Treat different namespaces as different people: rejected for combined cohorts because it silently assumes no overlap.
- Match names, dates, or other patient content inside Safira: rejected for privacy and correctness reasons, and outside scope.
- Require a universal identity broker: rejected as unnecessary infrastructure; an authorized custodian integration can provide the necessary versioned mapping.

## Decision 5: Make split membership patient-group based and protocol controlled

**Decision**: A versioned `EvaluationProtocol` supplies either complete patient-group assignments or deterministic allocation settings and constraints. The builder supports a simple stable hash-based group allocator only when the protocol supplies its role allocation intent, exact seed, algorithm version and applicable constraints. It performs one allocation using exactly that configuration, then validates group exclusivity, optional declared strata, required site/time rules, adequacy and feasibility. It never tries alternative seeds, chooses seed candidates by inspecting final-test outcomes, or changes constraints to force a fit. Infeasible scope returns `INSUFFICIENT_EVIDENCE` or `NOT_READY` with safe reasons even if an unapproved seed might yield a favorable allocation. Complex constraints can use supplied assignments.

**Rationale**: A deterministic assignment supports reproducibility, while supplied assignments allow approved designs with complicated site/time constraints. Explicit protocol settings avoid universal percentages or minimum counts. Checking constraints after assignment is simpler and auditable; a general-purpose constrained optimizer would add complexity and opportunities for test-set tuning.

**Alternatives considered**:
- Hard-code conventional percentages or sample minima: rejected because the project has not justified them.
- Row-level random splitting: rejected because it violates patient-level isolation.
- Search seeds until class balance or final-test adequacy looks favorable: rejected because this uses outcomes to tune the split.
- Implement a general optimizer for arbitrary constraints: rejected as disproportionate; infeasibility must be reported instead.

## Decision 6: Protect assignments through supplied prior manifests; keep storage external

**Decision**: The builder produces immutable manifests with exact protocol/version/configuration, assignment and source lineage. An explicitly injected custodian handoff receives the complete sensitive manifest for controlled persistence; ordinary results expose only a receipt and digest reference. Callers provide prior manifests, and an explicitly injected trusted integration checks their origin, source/version, requested and declared scope, completeness evidence, and relevant protected-test memberships against independently controlled custodian history. A manifest's self-asserted completeness, identifier or digest alone cannot establish verified coverage. Missing, partial, stale, conflicting or unverifiable history remains unknown and cannot support a cross-version protection claim; a protocol requiring verified history returns `NOT_READY`. The builder detects known changed membership or movement of previously protected patient groups into development. The package does not choose a database, export format or access-control service.

**Rationale**: The project has no dataset storage subsystem and has no runtime dependencies. Pure values are easy to test and do not silently create a new data store. Existing history can be checked by passing controlled manifests, while the responsible research environment retains them.

**Alternatives considered**:
- Add SQLite or another database to Feature 003: rejected because the requirement concerns research data protection, not catalog persistence; storage ownership and access policy belong to the study environment.
- Persist all rows and identifiers automatically in the repository or project workspace: rejected due privacy and restricted-data requirements.
- Trust a new seed/version to justify reassigning patients: rejected because prior protected membership must remain traceable and stable.

## Decision 7: Separate protected final-test artifact and ordinary development report

**Decision**: `DatasetBuildResult`, all of its ordinary serialization forms, and development-facing APIs contain only train/validation/calibration outputs, controlled non-row protected-test lifecycle status, a sensitive manifest reference, and a privacy-safe summary; they never contain protected-test rows, outcomes or correctness targets. The row-bearing artifact is transferred only through a separate explicit handoff to the protocol-authorized custodian. Before the protocol's release condition, only expressly allowed integrity/eligibility or structural summaries may be emitted. Release and reuse require the protocol's authorized lifecycle condition. The Python library does not claim to enforce operating-system access control against its caller, and adds no storage service.

**Rationale**: The final test must be assembled for future use but remain unavailable for model, feature, threshold, seed, eligibility or calibration choices. A separate artifact boundary makes that distinction visible and testable without adding a service. External restricted storage and custodian release remain operational responsibilities.

**Alternatives considered**:
- Return the protected artifact as a field on the ordinary `DatasetBuildResult`: rejected because development callers could access protected values even if summaries omit them.
- Add authentication, key management, or a secure enclave: rejected as disproportionate infrastructure and not requested by the spec.
- Hide final-test rows only in logs while returning them with all other rows: rejected because the ordinary API would still expose them.

## Decision 8: Validate leakage declarations; never fit or repair transforms

**Decision**: Preserve the classifier preprocessing identity from Feature 001 and Feature 002. Accept supplemental, versioned prediction/evidence-timing declarations and future safety-transform lineage only as explicit inputs. Check that permitted predictors were available at the prediction time and that any declared fitted safety transform used allowed development data only. Do not fit, impute, scale, select features, rebalance or train in this feature. Outcome, correctness, verification, group and partition fields are target/audit metadata, never predictor material.

**Rationale**: Feature 002 doesn't guarantee that every source supplies all timestamps needed by every research eligibility protocol. Those source-specific claims belong in a trusted supplemental integration. Recording them explicitly prevents the builder from inferring availability and keeps Feature 003 separated from future safety training.

**Alternatives considered**:
- Assume every evidence item was available at inference time: rejected because Feature 002 stores evidence semantics but is not a universal temporal provenance service.
- Fit and export preprocessing during dataset building: rejected because fitting must occur after patient grouping within a later approved safety workflow.
- Drop outcome-related fields without retaining audit lineage: rejected because target verification and reproducibility require controlled traceability.

## Decision 9: Use frozen values and standard-library canonical manifests

**Decision**: Follow Feature 002's frozen dataclass, recursive detach/freeze, tuple and detached serialization patterns. Canonical JSON-compatible manifests may use standard-library sorting and SHA-256 for deterministic comparison and tamper/change detection. Digest equality is never treated as evidence that a source identity, outcome or patient linkage is true.

**Rationale**: The repository has no runtime dependencies and existing collection values already provide a tested model for deep immutability. Canonicalization supports deterministic comparisons without adding a serialization package.

**Alternatives considered**:
- Add pandas/scikit-learn for assembly or splitting: rejected because the feature can join and group finite typed records without them, and they would bring unnecessary runtime dependencies.
- Store mutable DataFrames as the accepted dataset: rejected because mutation and index alignment would complicate privacy and immutability guarantees.
- Use a digest as a trust assertion: rejected because Feature 001/002 identity contracts already distinguish fingerprints from proof of object/source origin.
