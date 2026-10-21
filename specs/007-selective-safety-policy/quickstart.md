# Feature 007 Quickstart and Verification Guide

Feature 007 provides a **cohort-level research workflow** that selects and freezes one empirical TRUST cutoff per exact `(model_id, model_version, label_id)` scope. It does not provide per-patient inference, runtime status assignment, independent policy evaluation, clinical validation, or deployment readiness.

## Public operation

The public entry point is `PolicySelectionService.select`. Construct its protocol and evidence references from approved, independently verified inputs, then supply the exact Feature 001 registry and frozen Feature 005/006 artifacts:

```python
from safira.policy import PolicySelectionService

service = PolicySelectionService(registry, approved_policy_protocol, trusted_host_verifier)
outcomes = service.select(
    policy_dataset=new_policy_feature003_dataset,
    original_training_dataset=original_feature003_dataset,
    original_signal_protocol=original_feature004_protocol,
    estimator_artifacts={("model-a", "v1", "label-a"): frozen_estimator},
    calibrator_artifacts={("model-a", "v1", "label-a"): frozen_calibrator},
    prior_history=authoritative_prior_assignment_history,
)
```

`trusted_host_verifier` is explicitly injected by the host. It must execute and bind prediction admission, full dataset/target checks, protocol approval, artifact origin, and cross-source patient-disjointness checks. A constructed record, Boolean, digest, status, or check object supplied by an untrusted caller is not proof. The core validates returned typed checks against the exact submitted content and scope. The core library cannot authenticate hostile code controlling its trusted Python host. Because V1 success serialization includes cutoff, empirical risk/coverage, and eligible/selected counts, the approved protocol must explicitly set `disclose_support=True`; otherwise the service returns scope-local `NOT_READY` with no summary or artifact.

Shared admission failures raise privacy-safe `PolicyVerificationError`/`PolicyInputError`; the service does not publish scope results before the complete shared gate. Once shared admission succeeds, each exact scope produces a `PolicySelectionOutcome`: `SELECTED_UNEVALUATED` with an aggregate immutable artifact, or a safe non-success such as `INSUFFICIENT_EVIDENCE`, `NOT_READY`, `INVALID_INPUT`, `INCOMPATIBLE_INPUT`, or `NO_FEASIBLE_CUTOFF`.

## Evidence and selection boundary

- The policy input must be a new, independently authorized Feature 003 build whose validation partition was reserved for policy selection before outcomes were examined. Feature 005 validation and Feature 006 calibration evidence are spent and cannot be reused. Protected final-test evidence is never supplied or read.
- Original Feature 005/006 artifacts retain their original dataset and Feature 004 provenance. Feature 007 independently verifies their origin and reconstructs original Feature 004 references using only the original verified training predictors. Reference digests must match exactly; policy records are never used for fitting or refitting.
- Feature 007 independently verifies every original and policy Feature 002 prediction, every target, complete inventories, exact manifests, exact classifier/version/label scope, and authoritative patient-group disjointness before privately applying the frozen Feature 005 schema/preprocessing/estimator and Feature 006 mapping.
- Private scores, target values, patient-group keys, row keys, and intermediate signal records are ephemeral. They are not returned through public outcomes, artifacts, `repr`, or serialization.
- The protocol fixes one index assessment per patient/scope, the empirical risk ceiling, eligible/support rules, candidate cutoffs, comparison semantics, tie rule, and allowed aggregate disclosure before outcomes are accessed. Risk is incorrect TRUST-selected eligible patients divided by TRUST-selected eligible patients; coverage is TRUST-selected eligible patients divided by all eligible patients. Empty TRUST selection has undefined risk and cannot produce a successful artifact. Constant scores support only protocol-authorized all-or-none selection.
- Success means `SELECTED_UNEVALUATED`; policy evidence is spent. The selection-set empirical risk is not a statistical guarantee or an independent performance estimate. A later feature must evaluate the frozen policy on separately authorized independent evidence.

## Verification commands

From the Feature 007 worktree root in PowerShell, the tested environment used Python 3.11 with the approved `scikit-learn==1.7.1` dependency available ephemerally through `uv`. The commands below discover Feature 007 tests by their dedicated `test_policy*.py` files; this avoids counting unrelated Feature 005 tests that happen to match `-k policy`.

```powershell
$env:PYTHONPATH = 'src;tests'
$env:UV_CACHE_DIR = '.uv-cache'
$policyTests = @(Get-ChildItem tests -File -Filter 'test_policy*.py' | ForEach-Object { $_.FullName })
uv run --no-project --with pytest --with scikit-learn==1.7.1 python -m pytest -q $policyTests
$regressionTests = @(Get-ChildItem tests -File -Filter 'test_*.py' | Where-Object { $_.Name -notlike 'test_policy*.py' } | ForEach-Object { $_.FullName })
uv run --no-project --with pytest --with scikit-learn==1.7.1 python -m pytest -q $regressionTests
uv run --no-project --with pytest --with scikit-learn==1.7.1 python -m pytest -q
git diff --check
```

Verified after the focused remediation: dedicated Feature 007 suite **43 passed**; Feature 001–006 compatibility suite **751 passed**; complete suite **794 passed, 0 failed, 0 skipped**. `tests -k policy` selects **51 passed** because it includes the 43 Feature 007 tests and **8 pre-existing Feature 005 tests**; it is not the dedicated Feature 007 command. At the prior audit baseline, the corresponding counts were 37 dedicated Feature 007 tests, 45 selected by `-k policy` (including those same 8 Feature 005 tests), 751 Feature 001–006 tests, and 788 full-suite tests. These are synthetic software tests, not empirical clinical evaluation. `git diff --check` passed after this remediation.

## Known limitations

- No production policy-selection cohort, trusted policy/provenance ledger, cross-source patient linkage service, or custodian integration is configured. Without those inputs and an approved versioned protocol, shared admission fails closed; no successful operation is claimed.
- Existing Feature 004–006 public APIs deliberately do not expose reusable reference state or inference. The Feature 007 private bridge is coupled to their exact artifact schemas and internal frozen transformation semantics. It reconstructs and checks state rather than changing upstream contracts; incompatible or unreproducible state is rejected.
- The Feature 005 estimator and Feature 006 calibrator remain bound to their original training/calibration evidence. Feature 007 adds separate policy-selection evidence provenance and does not refit either artifact.
- No numerical ceiling, patient minimum, clinical cutoff, statistical risk guarantee, clinical validity, or deployment readiness is established by this implementation.
- Feature 008 runtime assessment and separate independent final evaluation remain outside Feature 007.
