import json

from safira.signals.records import (
    Feature003DatasetReference, SignalMethodConfig, SignalRunManifest, SignalSourceKey,
)


def test_run_manifest_is_detached_deterministic_and_has_no_restricted_values():
    reference = Feature003DatasetReference("d", "p", "1", "manifest-ref", "builder-v1")
    config = SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": 2})
    manifest = SignalRunManifest(reference, (SignalSourceKey("model", "v1", "label"),),
                                 (config,), exclusions=("signal_unavailable",))
    first = json.dumps(manifest.to_dict(), sort_keys=True)
    detached = manifest.to_dict()
    detached["method_configs"][0]["parameters"]["log_base"] = 10
    assert json.dumps(manifest.to_dict(), sort_keys=True) == first
    assert "patient" not in first.lower() and "outcome" not in first.lower()
    assert "correctness" not in first.lower() and "protected_test" not in first.lower()
    assert manifest.to_dict()["fold_algorithm"] == "sha256_seed_nul_group_mod_v1"
