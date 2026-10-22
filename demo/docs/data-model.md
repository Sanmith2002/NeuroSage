# Presentation and internal data model

These are proposed demo DTOs, not invented Safira constructors. Backend models forbid unknown properties recursively and serialize by explicit field construction. Frontend types are generated from the eventual OpenAPI. No generic object/metadata/value bags appear in presentation schemas.

## Public records

| Record | Fields and constraints |
|---|---|
| Health | `schema_version: "1"`, `state: "ready" | "not_ready"`, `execution_mode: "SYNTHETIC_TEST_ONLY"`, `baseline_commit` (fixed closure), `reason: "ready" | "initializing" | "configuration_invalid" | "fixture_unavailable"` |
| Lifecycle | `execution_mode: "SYNTHETIC_TEST_ONLY"`, `policy_status: "SELECTED_UNEVALUATED"`, `independent_evaluation_complete: false`, `protected_test_accessed: false`, `deployable: false`, `clinical_validity_established: false` |
| PipelineCatalog | `schema_version`, `baseline_commit`, `features: FeatureCard[8]`, `dimensions: SignalCard[6]`, `architecture: ArchitectureCard[3]`, `evidence: EvidenceRecord[]`, `limitations: Limitation[]`, `lifecycle: Lifecycle` |
| FeatureCard | `id: "001"…"008"`, `title`, `purpose`, `required_input`, `internal_operation`, `output_artifact`, `verification`, `failure_conditions: string[]`, `offline_preparation`, `runtime_role`, `predecessors: FeatureId[]`, `successors: FeatureId[]`, `diagram_kind` (fixed enum), `source_refs: SourceRef[]` |
| SignalCard | exact `dimension_id`, `title`, `purpose`, `input_dependency`, `availability_explanation`, `calculation_concept`, `missing_unsupported_behavior`, `estimator_contribution`, `method_ids: string[]` (approved catalog entries only), `source_refs` |
| ArchitectureCard | `component: "framework" | "backend" | "frontend"`, `title`, `responsibility`, `boundary` |
| SourceRef | `label`, `repository_path` (approved relative documentation/module path; display only, no file-serving route) |
| EvidenceRecord | `id`, `feature_ids`, `claim`, `kind: "historical_software_verification" | "fresh_phase1_verification" | "completion_record"`, `recorded_date` (ISO local date), `source_refs`, `qualification`; optional `passed`, `failed`, `skipped` integers only if source establishes them |
| Limitation | `id`, `title`, `description`, `scope: "software" | "scientific" | "host" | "clinical"` |
| ScenarioCatalog | `schema_version`, `scenarios: ScenarioSummary[]`, `lifecycle` |
| ScenarioSummary | `id: ScenarioId | null`, `title`, `purpose`, `scope: "controlled_synthetic_fixture"`, `category` (inventory category enum), `qualification: "qualified" | "pending" | "educational_only" | "unavailable"`, `runnable: boolean`, `unavailable_reason: null | fixed catalog code`, `evidence_note`, `limitations: string[]` |
| RunRequest | exactly `{scenario_id: ScenarioId}`; strict string, lowercase `s-` plus four hex characters, fixed allowlist; null/unknown IDs invalid |
| AssessmentRun | `kind: "assessment"`, `run_id` (fresh random UUID), `scenario_id`, `status: "TRUST" | "CAUTION" | "DEFER"`, `reason_code` (six framework result reasons only), `explanation` (server catalog text), `trace: TraceEntry[]`, `lifecycle` |
| RejectedRun | `kind: "rejected"`, `run_id`, `scenario_id`, `disposition: "REJECTED"`, `reason_code` (fixed framework admission allowlist), `explanation`, `trace`, `lifecycle`; **no assessment status** |
| ErrorEnvelope | `kind: "error"`, `request_id` (fresh UUID), `code` (HTTP matrix enum), `message` (fixed text); **no assessment or trace inference** |

Scenario category is pedagogical metadata. It must never supply a `/run` result. Qualified IDs are backed by service tests. Optional historical values omitted when unknown; never fill with invented zeros. Lifecycle flags describe the closed synthetic scope and must not be copied from unchecked caller data.

## Trace contract

TraceEntry fields: `id` (fixed stage/event enum), `title`, `state`, `evidence_kind`, `explanation` (fixed text), `feature_ids`. `state` is `historical_preparation | frozen_artifact_verified | runtime_executed | unavailable | skipped | rejected`; `evidence_kind` is `repository_record | host_callback_observed | service_result | service_exception | none`. No durations, raw exceptions, argument snapshots, receipt refs, digests or private values. Entries are assembled after service completion or safe rejection, in actual observation order. Historical rows are displayed in a separate group; order is not a fabricated execution clock.

| Entry | Valid evidence and semantics |
|---|---|
| Historical registration/dataset/training/calibration/policy | `historical_preparation` / `repository_record`; explains preparation of software/fixture package, never per-request fitting |
| Host checks: prediction, synthetic membership, original inventory, signal protocol, artifact origin, policy approval | `runtime_executed` / `host_callback_observed` only after delegated call actually returns. Explanation says callback returned; **not** whole-service verification passed. Aggregate repeated prediction callbacks, retaining observed order via first occurrence and count internally only; no fingerprint disclosure. |
| Frozen package verified | `frozen_artifact_verified` / `service_result` only when actual returned result proves complete shared admission; do not infer from origin callback alone |
| Service completed | `runtime_executed` / `service_result` with actual returned reason/status; for DEFER, required processing is non-ready but exact internal failing stage is unavailable |
| Frozen score/calibration/policy details | On TRUST/CAUTION, one grouped explanation states successful frozen application follows from service result and pinned source; **not separately timed or instrumented steps**. On DEFER mark details `unavailable` / `none`; no probability or fabricated successful policy comparison. |
| Service rejected | `rejected` / `service_exception`, fixed admission code; can occur during admission or later compatibility checks. Do not label an exact internal failing stage if only code is known. |
| Unobserved processing after rejection | `skipped` / `none` where source proves processing was not reached; otherwise `unavailable` / `none`. Do not infer all callbacks were verified simply because they returned. |

The wrapper may internally record method names and boolean completion, never values. It forwards calls unchanged, performs no verification itself, and does not catch/convert exceptions except to record that a delegated method raised and then rethrow. Core rejection of a returned receipt can occur after a successful callback. UI must retain this distinction. There is no claim of feature-by-feature live scoring telemetry.

## Internal host-only entities

- **ScenarioDefinition:** immutable ID, private recipe key, synthetic authority snapshot identifier, qualification evidence reference and expected status/reason for tests. Expected output is not used by execution adapter.
- **FixtureBundle:** actual Safira typed objects: registry, request and verifier; no serializers exposed to routes. Ledgers retain original trusted admission/protocol/origin facts separately from the submitted request. Freeze once setup completes.
- **QualificationEvidence:** baseline and lock hashes, recipe version, test node and actual outcome/rejection, approved publication decision; no private score/targets.
- **RunObservation:** callback enum and completion marker scoped to one invocation; discarded after mapping to presentation entries.

Relationships: one ScenarioDefinition resolves one approved FixtureBundle view; each invocation produces exactly one assessment, one rejection, or one internal error. Assessment has one lifecycle and trace list. No ORM, run-history store or patient entity is added. Public model/version/label aliases for the educational examples live in catalog prose; private association HMAC, artifact digests, patient/group/row IDs, correctness labels, raw predictions and score vectors are never public fields.
