# Phase 2 handoff

**Verdict:** READY FOR BACKEND IMPLEMENTATION. This is permission to implement Batch A next when requested, not a claim that the app or every outcome scenario already exists. Stop after Phase 1 in the current session.

- Worktree: `C:\Users\User\Desktop\NeuroSage-Workspace\safira-demo`.
- Branch: `demo/safira-fyp-showcase`.
- Baseline HEAD: `4f31886f12f6df09cd3dc688b48fb9e20329a3ee`.
- Shared Git repository, created from exact closure; no separate repository or framework copy. Original `safira-auto-training` worktree remains clean.
- Constitution: [v3.0.0](../../.specify/memory/constitution.md). Historical Feature 008 [closure](../../specs/008-runtime-safety-assessment/closure.md) binds synthetic-only use.
- No framework/public contract or root JS scaffolding changes are permitted by this plan. Demo is not Feature 009. Avoid Spec Kit scripts that mutate `.specify/feature.json` or allocate a numbered framework feature. All demo SDD lives here.

## Read before implementing

1. [spec](spec.md): 4 stories, 24 functional requirements, 7 nonfunctional requirements, 10 success criteria.
2. [research](research.md): actual constructors, verifier operations, fixture adaptation and evidence qualifications.
3. [feature guide](feature-guide.md) and [scenario inventory](scenario-inventory.md): exact science and conditional scenario publication.
4. [plan](plan.md), [API](api-contract.md), [data model](data-model.md), [UI](ui-design.md).
5. [tasks](tasks.md): 24 pending tasks, 6 per batch. Start A01, tests before implementation.
6. [consistency analysis](consistency-analysis.md) and [requirements checklist](checklists/requirements.md).

## Exact integration references

- `src/safira/runtime/_service.py`: `simulate_synthetic_assessment(request, *, registry, verifier)`.
- `_records.py`: strict SyntheticRuntimeRequest constructor, internal result and association HMAC.
- `_verification.py`: six RuntimeVerifier operations and exact bundle admission.
- `_signals.py`: original train-only reference recovery and private Feature 004 derivation.
- `_scoring.py`: existing frozen Feature 005 reconstruction and Feature 006 mapping.
- `_policy.py`: exact policy `>=`/`>` comparison, no separate DEFER threshold.
- `_exceptions.py`: safe admission vs readiness reasons.
- `tests/runtime_fixtures.py`: controlled builder and SyntheticRuntimeVerifier.
- `tests/policy_fixtures.py`: real preparation services, separate selection cohort, baseline/logistic recipes.
- `tests/collection_fixtures.py`: loader-owned registry fixture and deterministic synthetic adapter.
- `tests/signals_fixtures.py`, `tests/training_fixtures.py`, `tests/test_calibration_bundle_gate.py`: independent synthetic ledgers/origin authority. These are test references, not runtime imports.
- Existing eight `tests/test_runtime_*.py` files: 45 nodes, including both real integration and deliberately isolated monkeypatch tests. Do not mistake helper coverage for a complete runnable scenario.

## Environment status

Fresh `.venv` in demo checkout created using `uv venv .venv --python 3.11`; resolved Python is **3.11.17**, not audit Python 3.11.0. Installed current checkout editable and pytest 9.1.1. Exact freeze is [phase1-environment.txt](phase1-environment.txt). Safira import location confirmed in current checkout. Existing runtime suite passed 45/45 in 33.59 s; a later corrected disposable probe confirmed natural TRUST/CAUTION and repeated one boundary test (not an additional unique suite node). No FastAPI/frontend dependencies installed, no backend/frontend functional code written, no production build claimed. Full 839-suite result remains historical only.

## Decisions that must not drift

IDs only at POST. Status only from actual private service. Host-constructed synthetic authority only. No individual score or full internal result serialization. No monkeypatching/instrumenting service globals. Forward verifier calls unchanged and describe observations conservatively. A returned callback is not complete admission. DEFER substage detail remains unavailable. Missing selected policy prevents valid request construction. Default real fixture only uses entropy; all six signal families remain educationally explorable without pretending they ran. Fixtures prepare/freeze before worker readiness, never fit during a run. No protected final-test content is loaded.

## Known limitations, not Phase 1 blockers

Test factories require demo-owned host assembly because they depend on pytest and test imports. No generic installed fixture-host factory is available. A corrected disposable probe confirmed natural TRUST and CAUTION recipes (see research); demo-host qualification still remains. DEFER and full explanation/reference service scenarios remain conditional. There is no production trust custody, independent policy evaluation or clinical validation. Detailed runtime telemetry is absent; use the safe coarse trace design. Phase 1 setup/docs are uncommitted for review; no commit/push or functional implementation is implied.
