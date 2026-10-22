# Phase 1 consistency analysis

Date: 2026-10-22. Analysis is of SDD and repository integration feasibility, not acceptance of a functional application. No critical/high unresolved design inconsistency found. Implementation/qualification work is intentionally pending.

## Traceability

Task references `FR-nnn`, `SC-nnn` and `NFR-nnn` abbreviate canonical `DEMO-FR-nnn`, `DEMO-SC-nnn`, `DEMO-NFR-nnn` from spec.md. There are 4 user stories, 24 distinct functional requirements, 7 nonfunctional requirements, 10 success criteria and 24 pending implementation tasks (6 in each batch).

| Story / requirement group | Contract/design | Implementation / acceptance tasks |
|---|---|---|
| US-01; FR-001/002 | ui-design Dashboard/shell, PipelineCatalog | B02/B03, D02 |
| US-02; FR-003/004/005/006 | feature-guide, ui-design Explorer, FeatureCard/SignalCard | B04/B05/B06, C04, D02 |
| US-03; FR-007/008/010/011/012 | research, fixture inventory, plan host lifecycle | A01/A02/A03/A05/A06, C03/C06, D01/D03 |
| US-03; FR-009/013/014 | API matrix and RunRequest/result union | A04/A05, C01/C03/C05, D01 |
| US-03; FR-015/016 | scenario inventory, qualification/runnable schema | A03/A05, C02/C06, D05/D06 |
| US-03; FR-017/018 | trace truth table, explicit allowlists | A04/A05, C04/C05, D01/D02 |
| US-04; FR-019/020/021 | attributed evidence, lifecycle, route absence | B03/B06, A05, C05, D01/D05 |
| FR-022/023/024 | plan local configuration, locks and quickstart | A01/A06/B01, C01, D03/D04/D06 |
| NFR-001/002 | accessibility/responsive design | B02/B05, D02 |
| NFR-003/007 | exact baseline, locks, recipe proof | A01/A03, D03/D04 |
| NFR-004/005/006 | safe DTOs, worker/readiness, typed component boundaries | A04/A05/A06, C01/C03, D01/D04 |
| SC-001–010 | source and implementation gates in spec/tasks | Individual task mappings plus D06 final review |

## Resolved findings

| Finding | Resolution |
|---|---|
| Target absent but Git worktree metadata occupied path | Inspected dry-run, removed only stale registration; created desired new branch at exact baseline. Old branch preserved. |
| Early specification headers conflict with later completion evidence | Research evidence table attributes earlier completion records/checked tasks and later audit history; does not invent 001–004 closure files. |
| Test fixtures are pytest-coupled, not installed application factories | Demo-owned host assembly using actual framework services; tests may compare original factories, running app may not import them. |
| Some status tests inject score/readiness results | Distinguish isolated tests from qualifying real runs. Disposable unmocked probe confirmed natural TRUST and CAUTION. DEFER remains gated. |
| Missing policy cannot form a valid request | Unavailable catalog category/startup negative, not successful DEFER or forced service scenario. |
| Unsupported explanation has no numerical reliability predictor | Educational availability explanation, no claim it independently triggers DEFER. |
| Default factory has entropy only | All six dimensions explained; only configured methods described as processed. kNN/domain unit reconstruction coverage not promoted to full-service proof. |
| No granular service telemetry | Forward-only request-local verifier observations plus final result. Callback completion does not establish full core admission; unobserved internals marked unavailable. |
| Internal result contains association HMAC and artifact digests | Smaller explicit HTTP projection excludes them and all private values; no wholesale `to_dict()`. |
| Timeout cannot safely stop a Python thread | Dedicated prepared subprocess, fixed slot/deadline; terminate on timeout, remain not-ready until explicit restart. No fitting during POST. |
| Root checkout already has JavaScript application scaffolding | Independent `demo/frontend` package and lock; inherited root files untouched. |
| Historical/full-suite counts could be mistaken for new verification | Historical 839 separate from fresh 45; one repeated boundary test overlaps, not added. Different Python environments disclosed. |

## Remaining implementation gates

No FastAPI/React implementation or dependency lock for the app exists. Batch A must qualify adapted host recipes and safe worker IPC. DEFER full-service recipe may remain unsupported and must be visible as such. Browser, security, full regression and production build evidence are future Batch D deliverables. This is readiness for backend implementation, not readiness for a completed viva or clinical deployment.

## Phase 1 final checks

- Exact branch/HEAD and closure ancestry verified.
- Original worktree clean; framework/tests/specs/packaging show no tracked difference against closure.
- All new tracked-intent artifacts restricted to `demo/`; `.venv` ignored.
- Required nine SDD files plus feature/scenario/analysis/checklist and reproducibility evidence present; internal local links and counts checked.
- No functional app code, duplicate Safira source, protected test access, Feature 009 work, raw score response or clinical claim introduced.
- Whitespace checked with `git diff --check`; new untracked document contents additionally checked using `git diff --no-index --check` against an empty tree because ordinary Git diff does not inspect untracked files.

See [requirements checklist](checklists/requirements.md) for all 18 user quality gates. The final source status remains uncommitted for review.
