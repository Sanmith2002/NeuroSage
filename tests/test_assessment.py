import pytest

from safira import SafetyAssessment, SafetyStatus


def test_create_safety_assessment():
    assessment = SafetyAssessment(
        patient_id="P001",
        label="AD",
        prediction_probability=0.91,
        reliability_score=0.86,
        status=SafetyStatus.TRUST,
    )

    assert assessment.patient_id == "P001"
    assert assessment.label == "AD"
    assert assessment.prediction_probability == 0.91
    assert assessment.reliability_score == 0.86
    assert assessment.status == SafetyStatus.TRUST


def test_assessment_to_dict():
    assessment = SafetyAssessment(
        patient_id="P001",
        label="AD",
        status=SafetyStatus.CAUTION,
    )

    result = assessment.to_dict()

    assert result["patient_id"] == "P001"
    assert result["label"] == "AD"
    assert result["status"] == "CAUTION"


def test_invalid_prediction_probability():
    with pytest.raises(ValueError):
        SafetyAssessment(
            patient_id="P001",
            label="AD",
            prediction_probability=1.5,
        )


def test_empty_patient_id():
    with pytest.raises(ValueError):
        SafetyAssessment(
            patient_id="",
            label="AD",
        )


def test_empty_label():
    with pytest.raises(ValueError):
        SafetyAssessment(
            patient_id="P001",
            label="",
        )