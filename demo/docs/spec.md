# Demo specification

Status: Phase 1 complete; implementation pending. Date: 2026-10-22 (Asia/Colombo).
Baseline: `4f31886f12f6df09cd3dc688b48fb9e20329a3ee`. This is an application demonstration, not Feature 009 or independent evaluation. Constitution v3.0.0 governs claims, privacy and evidence boundaries.

## Personas and user stories

- **US-01, presenter, P1:** Open a dashboard that establishes Safira's purpose, exact software baseline, eight features and research limitations. Acceptance: project identity, architecture, source-attributed historical verification, scenario availability and links to all four screens are visible without running a scenario.
- **US-02, evaluator, P1:** Select any of eight stages and inspect purpose, inputs, operation, artifact, verification, failure conditions, lifecycle and dependencies. Acceptance: all eight stages are independently keyboard-selectable; six signal families use exact framework identifiers; educational diagrams are explicitly separate from observed execution.
- **US-03, presenter, P1:** Run an approved synthetic scenario and explain its actual outcome. Acceptance: only an opaque approved ID is submitted; one real Feature 008 invocation supplies the outcome; trace entries cite host observations or result evidence; admission rejection cannot become DEFER. Unproven scenario categories are unavailable with an explanation.
- **US-04, evaluator, P1:** Inspect scientific lifecycle and limits. Acceptance: historical test results have source/date attribution, selection remains unevaluated, protected final testing remains isolated, and software verification is never described as clinical performance.

## Functional requirements

| ID | Requirement | Primary acceptance evidence |
|---|---|---|
| DEMO-FR-001 | Provide Dashboard, Framework Explorer, Simulation Lab, Evidence & Limitations with deep links and persistent research banner. | Four routes and navigation/browser tests |
| DEMO-FR-002 | Dashboard shows identity, research purpose, eight-feature overview, three-component architecture, verification and available scenarios. | Dashboard content test |
| DEMO-FR-003 | Explorer independently selects Features 001–008 and exposes all eight explanatory fields. | Feature catalog schema and selection tests |
| DEMO-FR-004 | Present exact six Feature 004 dimensions, their prerequisites, methods and all availability states. | Source comparison against `signals/base.py` |
| DEMO-FR-005 | Explain independent train, validation, calibration, policy-selection and protected final-test evidence and model-qualified label scope. | Feature catalog and lifecycle review |
| DEMO-FR-006 | Separate historical preparation, frozen verification and observed runtime; never portray training/calibration/selection as running per request. | Trace contract tests |
| DEMO-FR-007 | Import installed Safira from this checkout; preserve Features 001–008 and private API boundary. | Import-origin and source-diff gates |
| DEMO-FR-008 | Resolve only server-owned immutable scenario definitions and locally controlled synthetic authority. | Registry allowlist/unknown-ID tests |
| DEMO-FR-009 | POST accepts exactly one strict opaque `scenario_id`; reject all extra fields and unsupported media types. | Malicious/oversized request tests |
| DEMO-FR-010 | Invoke `simulate_synthetic_assessment(request, registry=..., verifier=...)` for every published assessment scenario. | Unmocked integration tests; fail if service is unavailable |
| DEMO-FR-011 | Supply all six trusted RuntimeVerifier operations with exact independent fixture-ledger bindings. | Missing/mismatched receipt and ledger-entry negatives |
| DEMO-FR-012 | Apply existing frozen signal, estimator, calibration and policy logic only; do not recreate algorithms or tune artifacts during a run. | Digest immutability and fitting-call guard tests |
| DEMO-FR-013 | Render TRUST/CAUTION/DEFER only from returned framework status; represent admission failure as request-level REJECTED. | Discriminated response/status tests |
| DEMO-FR-014 | Distinguish input validation, unavailable scenario, expected admission failure and unexpected server error with fixed safe messages. | HTTP error matrix tests |
| DEMO-FR-015 | Publish runnable scenarios only after real fixture construction and unmocked expected-behavior verification. | Scenario evidence manifest and startup gate |
| DEMO-FR-016 | Explain unsupported categories without forcing a scenario, score, missing policy or fabricated success. | Disabled catalog and UI tests |
| DEMO-FR-017 | Generate trace from request-local verifier observations plus final service result; no fake step-level telemetry. | Early rejection and interrupted-verifier traces |
| DEMO-FR-018 | Serialize only explicit presentation allowlists; exclude private values, source ledgers and association bindings from responses/logs. | Recursive schema and canary scans |
| DEMO-FR-019 | Evidence screen attributes feature completion and historical software counts to repository sources, distinguishing fresh checks. | Evidence catalog/source review |
| DEMO-FR-020 | Persist research-only lifecycle, unevaluated policy, missing independent evaluation and absence of clinical authorization on all result views. | Lifecycle constant tests |
| DEMO-FR-021 | Keep all patient-data input, upload, arbitrary artifact/threshold/verifier/code submission and protected-test access absent. | Route inventory and negative tests |
| DEMO-FR-022 | Use loopback-only startup, exact host/origin rules, bounded execution and fail-closed readiness. | Startup/security tests |
| DEMO-FR-023 | Provide reproducible separate demo environments, dependency locks, Windows startup and viva instructions. | Clean-install rehearsal |
| DEMO-FR-024 | Keep application in `demo/`, with frontend using only typed HTTP contracts and backend using current installed Safira. | Dependency/static boundary review |

## Nonfunctional requirements

- **DEMO-NFR-001 accessibility:** WCAG 2.2 AA design target; keyboard navigation, visible focus, semantic landmarks, screen-reader status announcements, reduced motion and text plus icons for every state. Verify automated checks and manual keyboard flows; do not claim certification.
- **DEMO-NFR-002 responsiveness:** usable at 360, 768 and 1280+ CSS pixels without page-wide horizontal scrolling. Long code identifiers wrap.
- **DEMO-NFR-003 determinism:** exact same locked environment and server scenario manifest reproduce expected status/reason; no cross-platform bitwise guarantee.
- **DEMO-NFR-004 privacy:** no disk run history, body logging, private exception payloads or sensitive response fields. Use fresh opaque correlation IDs only.
- **DEMO-NFR-005 reliability:** one active simulation; bounded request size and worker timeout; unexpected failures remain errors. Fixture initialization completes before readiness.
- **DEMO-NFR-006 maintainability:** strict TypeScript and typed backend models; contract types generated from OpenAPI in Phase 2. No database service, cloud account or Docker requirement; framework registry uses its own temporary local SQLite catalog.
- **DEMO-NFR-007 reproducibility:** exact resolved direct/transitive versions locked per component, with framework sklearn pin preserved. Record OS, Python, Node, lock hashes and baseline. Phase 1 environment differs from historical audit and is identified separately.

## Success criteria

1. **DEMO-SC-001:** Requested worktree/branch starts at exact closure; only `demo/` tracked changes; original source remains unchanged.
2. **DEMO-SC-002:** All four screens and eight feature explanations meet US-01–04 acceptance.
3. **DEMO-SC-003:** Import resolves to this checkout and real private service executes without mocked scoring/statuses.
4. **DEMO-SC-004:** Every published scenario has an unmocked proof, exact fixture recipe and expected result/rejection; no outcome category is silently promised.
5. **DEMO-SC-005:** Invalid trust always yields rejection without assessment; admitted non-ready evidence yields DEFER only where the actual service supports it.
6. **DEMO-SC-006:** Every observed trace event has recorded host or service evidence; unobserved details are unavailable or skipped.
7. **DEMO-SC-007:** Adversarial request, response, log and protected-access tests pass with no prohibited data disclosure or fitting during run.
8. **DEMO-SC-008:** Historical verification and scientific limitations stay accurate across API/UI and viva material.
9. **DEMO-SC-009:** Backend/frontend/component/browser checks, production frontend build and full framework regressions pass in Batch D.
10. **DEMO-SC-010:** Fresh Windows rehearsal follows locked install/start instructions; source diff and whitespace gates pass.

Phase 1 satisfies the documentation/setup gates only. Application acceptance criteria are planned tests, not already achieved results.
