from dataclasses import replace

import pytest

from safira.signals.exceptions import SignalInputError
from safira.signals.records import SignalMethodConfig, SignalSourceKey
from safira.signals.reference import (
    ReferenceCompatibilityKey,
    ReferenceFitConfig,
    ReferenceObservation,
    fit_knn_reference,
    fit_domain_reference,
    apply_knn_reference,
)


def inputs():
    source = SignalSourceKey("model", "v3", "label")
    key = ReferenceCompatibilityKey(source, "knn_distance", "v1", {"k": 1, "metric": "euclidean"},
                                    "vector-v1", "preprocess-v1", "dataset-v1", "protocol-v1", "2",
                                    "manifest-v1", "training-cohort")
    cfg = ReferenceFitConfig(key, SignalMethodConfig("knn_distance", "v1", {"k": 1, "metric": "euclidean"}),
                             2, "fixed-seed")
    rows = tuple(ReferenceObservation(f"train-{i}", source, f"g{i}", "vector-v1", "preprocess-v1",
                                     (float(i), float(i + 1)), evidence_ref=f"ev-{i}") for i in range(4))
    return key, cfg, rows


def test_final_fit_uses_only_supplied_training_predictor_evidence():
    key, cfg, training = inputs()
    baseline = fit_knn_reference(training, cfg)
    # Held-out collections are deliberately not accepted by the fit function.
    assert fit_knn_reference(training, cfg) == baseline
    with pytest.raises(SignalInputError):
        ReferenceObservation("validation", key.source_key, "held-v", "vector-v1", "preprocess-v1",
                             (999.0, 999.0), evidence_ref="ev-v", partition_role="validation")
    with pytest.raises(SignalInputError):
        ReferenceObservation("protected", key.source_key, "held-p", "vector-v1", "preprocess-v1",
                             (-999.0, -999.0), evidence_ref="ev-p", partition_role="protected_test")
    with pytest.raises(TypeError):
        ReferenceObservation("bad", key.source_key, "g", "vector-v1", "preprocess-v1",
                             (1.0, 1.0), evidence_ref="ev-bad", correctness_target=1)


def test_validation_and_calibration_apply_frozen_state_without_refit():
    key, cfg, training = inputs()
    state = fit_knn_reference(training, cfg)
    before = state
    validation_score = apply_knn_reference(state, (2.0, 3.0), key, query_evidence_ref="validation-evidence")
    calibration_score = apply_knn_reference(state, (3.0, 4.0), key, query_evidence_ref="calibration-evidence")
    assert validation_score.state == "available" and validation_score.value >= 0
    assert validation_score.compatibility_key == key
    assert validation_score.method_config == cfg.method_config
    assert validation_score.reference_digest == state.digest
    assert set(state.evidence_refs).issubset(validation_score.evidence_refs)
    assert "validation-evidence" in validation_score.evidence_refs
    assert calibration_score.state == "available" and calibration_score.value >= 0
    assert state is before


def test_reproducible_fit_ignores_row_order_and_opaque_group_renaming():
    key, cfg, training = inputs()
    state = fit_knn_reference(training, cfg)
    renamed = tuple(replace(row, patient_group_ref=f"opaque-{i}") for i, row in enumerate(training))
    assert fit_knn_reference(tuple(reversed(training)), cfg).digest == state.digest
    assert fit_knn_reference(renamed, cfg).digest == state.digest


def test_domain_final_state_is_training_only_and_detached():
    source = SignalSourceKey("model", "v3", "label")
    parameters = {"category_field": "declared-domain", "category_mapping_version": "mapping-v1",
                  "privacy_approval_ref": "approval-reference"}
    key = ReferenceCompatibilityKey(source, "domain_familiarity", "v1", parameters, "domain-schema", "prep",
                                    "dataset", "protocol", "1", "manifest", "cohort")
    cfg = ReferenceFitConfig(key, SignalMethodConfig("domain_familiarity", "v1", parameters), 2, "seed")
    category = ["cohort-a"]
    rows = (ReferenceObservation("r1", source, "g1", "domain-schema", "prep", domain_category=category[0], evidence_ref="ev-1"),
            ReferenceObservation("r2", source, "g2", "domain-schema", "prep", domain_category="cohort-b", evidence_ref="ev-2"))
    state = fit_domain_reference(rows, cfg)
    category[0] = "mutated"
    assert "cohort-a" not in repr(state)
    assert state.digest
    assert not hasattr(state, "patient_group_ref")
    assert not hasattr(state, "reference_group_refs")
