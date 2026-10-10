import pytest

from safira import SafetyContext


def test_create_minimal_safety_context():
    context = SafetyContext(
        patient_id="P001",
        label="AD",
    )

    assert context.patient_id == "P001"
    assert context.label == "AD"
    assert context.prediction is None
    assert context.prediction_probability is None


def test_create_full_safety_context():
    context = SafetyContext(
        patient_id="P001",
        label="AD",
        patient_data={"MRI": "example"},
        prediction=1,
        prediction_probability=0.91,
        available_modalities=["MRI", "clinical"],
        feature_representation=[0.1, 0.2, 0.3],
        repeated_outputs=[0.91, 0.88, 0.93],
        modality_outputs={
            "MRI": 0.94,
            "clinical": 0.83,
        },
        domain_metadata={
            "dataset": "ADNI",
        },
        explanation={
            "type": "example",
        },
    )

    availability = context.evidence_availability()

    assert availability["patient_data"] is True
    assert availability["prediction"] is True
    assert availability["prediction_probability"] is True
    assert availability["feature_representation"] is True
    assert availability["repeated_outputs"] is True
    assert availability["modality_outputs"] is True
    assert availability["domain_metadata"] is True
    assert availability["explanation"] is True


def test_minimal_context_reports_missing_evidence():
    context = SafetyContext(
        patient_id="P001",
        label="AD",
    )

    availability = context.evidence_availability()

    assert availability["feature_representation"] is False
    assert availability["repeated_outputs"] is False
    assert availability["modality_outputs"] is False
    assert availability["domain_metadata"] is False
    assert availability["explanation"] is False


def test_invalid_context_prediction_probability():
    with pytest.raises(ValueError):
        SafetyContext(
            patient_id="P001",
            label="AD",
            prediction_probability=1.5,
        )


def test_empty_context_patient_id():
    with pytest.raises(ValueError):
        SafetyContext(
            patient_id="",
            label="AD",
        )


def test_empty_context_label():
    with pytest.raises(ValueError):
        SafetyContext(
            patient_id="P001",
            label="",
        )


def test_context_mutable_defaults_are_independent():
    context_a = SafetyContext(
        patient_id="P001",
        label="AD",
    )

    context_b = SafetyContext(
        patient_id="P002",
        label="AD",
    )

    context_a.available_modalities.append("MRI")

    assert context_a.available_modalities == ["MRI"]
    assert context_b.available_modalities == []