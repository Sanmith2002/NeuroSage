# Feature 007 Closure Record

**Status**: Closed within approved research-software scope  
**Audit date**: 2026-10-22  
**Audited branch/worktree**: `feature-07/Selective-Safety-Policy` at `C:/Users/User/Desktop/NeuroSage-Workspace/safira-auto-training`

## Verified commits and ancestry

- Feature 006 closure ancestor: `12d1dc656e6f54f76e154d67372002bf20e439a6` (`Feature 006 closure`); confirmed ancestor of Feature 007.
- Initial Feature 007 implementation: `96c01a4ca4ce490361aa04b62f6d7f4be4ba2af9`.
- Final verified implementation and remediation: `0328475f718b89acbf7e72d3bc0da05e6757bb57` (`Feature 007 adversarial verification + focused remediation`). This commit records the seven remediation files and tests.
- Closure documentation commit: recorded in Git history after this record was written.
- All 36 Feature 007 tasks remain checked.
- The shared Spec Kit prerequisite resolver defaults to Feature 006 in `.specify/feature.json`. For this audit it was invoked with the read-only `SPECIFY_FEATURE_DIRECTORY=specs/007-selective-safety-policy` override and `SPECIFY_FEATURE_NO_PERSIST=1`; it resolved the Feature 007 spec, tasks, and supporting documents without changing resolver state.

## Adversarial audit

The prior adversarial audit passed gates A–H and J and identified gate I as requiring remediation. Gate I is reverified as passing. Targeted gates A–F also pass:

- **A — Scope-local failure isolation**: complete shared admission precedes scope processing. Each scope is handled independently in sorted source-key order. Ambiguous index selection, unavailable reference reconstruction, insufficient support, scoring/numerical failure, and scope incompatibility map to safe scope-local non-success outcomes without artifacts; no-feasible-cutoff is returned by the selection routine as a typed non-success and also has no artifact. Successful sibling scopes retain `SELECTED_UNEVALUATED` artifacts. Only documented failure codes and typed signal errors are handled locally; unexpected exceptions are not converted to `NOT_READY`.
- **B — Atomic shared trust failures**: protocol approval, exact source/artifact inventories, Feature 002 and dataset admission, Feature 005/006 origin, complete ground-truth checks, patient history/disjointness, and original provenance are verified before outcomes are used. Their failures occur outside the scope-local handlers and cannot return partial accepted outcomes. A missing scope-local reference reconstruction remains distinguishable from forged shared origin or admission evidence.
- **C — Feature 004 reference reconstruction**: references are rebuilt from original training rows only, with exact declared method, version, parameters, evidence schema, preprocessing identity, and compatibility key. Reconstructed state digests must equal frozen manifest digests. Policy rows are derived from admitted predictions and only apply the frozen state; no caller-supplied signal rows are accepted. kNN training vectors exclude the policy query, and the synthetic out-of-sample `[10, 10]` query against the approved four-vector training reference produces `sqrt(162) ≈ 12.727922`. Unapproved schema and altered frozen digest are rejected. Frozen Feature 005 scoring and Feature 006 mapping are reconstructed through their existing private scoring path.
- **D — Non-monotonic risk**: all permitted cutoff candidates are evaluated. The regression for scores `0.9, 0.8, 0.7, 0.6`, correctness `1, 0, 1, 1`, candidates `0.9, 0.8, 0.6`, and ceiling `0.3` selects `0.6`, with empirical risk `0.25` and coverage `1.0`.
- **E — Privacy and lifecycle**: outcomes and errors expose only allowlisted aggregate data, safe reason codes, and exact scope metadata; patient/group/assessment identifiers, row evidence, raw targets, and individual scores are not serialized or included in representations. Non-success outcomes have no artifact. Success is `SELECTED_UNEVALUATED`; selection evidence is spent, independent evaluation is incomplete, protected final-test access is false, deployable is false, and clinical validity is not established. The public policy surface has no patient-level scoring or `SafetyAssessment` operation.
- **F — Regression**: see the exact run counts below. All 36 task checkboxes remain complete. The exact Feature 007 file list was used for the 43-node dedicated test run; the eight pre-existing Feature 005 policy-filtered tests were not added to that count.

The seven-file remediation modifies only `specs/007-selective-safety-policy/quickstart.md`, Feature 007 policy modules (`references.py`, `service.py`, `signals.py`), and their focused tests (`test_policy_multiscope.py`, `test_policy_reference_reconstruction.py`, `test_policy_selection.py`). No Feature 001–006 source-contract changes were found.

## Regression evidence

Executed with the repository's `uv` environment and scikit-learn `1.7.1`:

| Run | Result |
|---|---:|
| Focused remediation files | 18 passed |
| Exact Feature 007 test files | 43 passed |
| Existing Feature 001–006 tests | 751 passed |
| Full `python -m pytest -q` suite | 794 passed, 0 failed, 0 skipped |
| `git diff --check` on the audited working tree | Passed |

The unique node total is `43 + 751 = 794`; the full-suite result confirms the partition.

## Method and limits

For each exact `(model_id, model_version, label_id)` scope, the approved patient-level index-assessment rule chooses the lexicographically earliest assessment reference before correctness outcomes are considered. The implementation evaluates all approved candidate cutoffs and chooses maximum eligible-patient coverage among candidates meeting the empirical risk ceiling and support requirements, applying the predeclared deterministic tie rule. Empirical risk is incorrect selected eligible patients divided by selected eligible patients; coverage is selected eligible patients divided by all eligible patients. This is a selection-cohort result, not a guarantee about future risk.

The workflow preserves frozen Feature 005 estimator and Feature 006 calibrator provenance and verifies their binding to original Feature 003/004 evidence. Feature 004 reference equivalence is based on training-only reconstruction and exact frozen digest matching. Policy selection uses a separate authorized cohort, and the protected final-test boundary remains untouched.

The trusted host must provide authentic prediction admission, protocol approval, artifact origin, target verification, patient linkage, and complete authoritative history. Production ledgers, cross-source linkage, custodian integration, and a configured production selection cohort are not supplied by this research-software feature. The implementation makes no independent policy evaluation, empirical future-risk guarantee, clinical validity claim, or deployment authorization. A later separately scoped feature must conduct independent evaluation on authorized evidence.

Feature 007 is ready for the next separately scoped research feature. No Feature 008 work is included in this closure.
