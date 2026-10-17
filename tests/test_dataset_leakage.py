import pytest

from safira.dataset import DatasetLeakageError, EvidenceTimingDeclaration
from safira.dataset.validation import validate_predictor_separation, validate_timing, validate_transformations
from safira.dataset import TimingVerification, TransformationDeclaration, TransformationVerification
from safira.dataset.verification import validate_timing_check, validate_transformation_check
from safira.dataset.exceptions import DatasetVerificationFailed


def test_outcome_identity_and_role_cannot_be_predictor_material():
    with pytest.raises(DatasetLeakageError):
        validate_predictor_separation({"feature","correctness_target"})
    validate_predictor_separation({"feature_representation","primary_score"})


def test_timing_requires_exact_occurrence_verified_state_and_prediction_time():
    prediction=type("R",(),{"source_key":("m","v1","l"),"association":type("A",(),{"occurrence_ref":"o"})(),
        "provenance":type("P",(),{"details":{"predicted_at":"2026-01-02T00:00:00Z"}})()})()
    declaration=EvidenceTimingDeclaration(prediction.source_key,"o","feature_representation","2026-01-01T00:00:00Z","verified")
    validate_timing(prediction,(declaration,),required_categories=("feature_representation",))
    late=EvidenceTimingDeclaration(prediction.source_key,"o","feature_representation","2026-01-03T00:00:00Z","verified")
    with pytest.raises(DatasetLeakageError): validate_timing(prediction,(late,))
    wrong=EvidenceTimingDeclaration(prediction.source_key,"other","feature_representation","2026-01-01T00:00:00Z","verified")
    with pytest.raises(DatasetLeakageError): validate_timing(prediction,(wrong,),required_categories=("feature_representation",))


def test_transform_fit_on_held_out_patient_or_wrong_preprocessing_fails():
    with pytest.raises(DatasetLeakageError): validate_transformations(({"fitted_on_groups":{"g2"},"preprocessing_identity":"p","expected_preprocessing_identity":"p"},),{"g2"})
    with pytest.raises(DatasetLeakageError): validate_transformations(({"fitted_on_groups":{"g1"},"preprocessing_identity":"changed","expected_preprocessing_identity":"registered"},),{"g2"})


def test_timing_and_transform_claims_require_exact_trusted_checks():
    timing=EvidenceTimingDeclaration(("m","v1","l"),"o","feature","2026-01-01T00:00:00Z","verified")
    check=TimingVerification(timing.source_key,timing.occurrence_ref,timing.category,timing.available_at,"verified",authority="source",method="ledger",evidence_ref="source-check")
    validate_timing_check(check,timing)
    with pytest.raises(DatasetVerificationFailed): validate_timing_check(True,timing)
    transform=TransformationDeclaration("t","v1",("m","v1","l"),"preprocess-v1")
    tcheck=TransformationVerification("t","v1",transform.source_key,"verified",authority="custodian",method="lineage-ledger",evidence_ref="lineage-check")
    validate_transformation_check(tcheck,transform)
    with pytest.raises(DatasetVerificationFailed): validate_transformation_check(True,transform)
