from dataclasses import FrozenInstanceError, replace
import json

import pytest


def _artifact(registered_collection):
    from test_training_acceptance import _make_service
    _, dataset, signals, _, _, service = _make_service(registered_collection)
    return service.train(dataset, signals)[0].artifact


def _digest(value):
    import hashlib
    import json
    return hashlib.sha256(json.dumps({"value": value}, sort_keys=True, separators=(",", ":"),
                                     default=list).encode()).hexdigest()


def test_artifact_export_is_detached_private_and_marks_selection_lifecycle(registered_collection):
    artifact = _artifact(registered_collection)
    payload = artifact.to_dict()
    before = json.dumps(payload, sort_keys=True)
    payload["scope"]["model_id"] = "changed"
    payload["feature_schema"]["columns"][0]["name"] = "changed"
    assert json.dumps(artifact.to_dict(), sort_keys=True) == before
    serialized = json.dumps(artifact.to_dict(), sort_keys=True).lower()
    for forbidden in ("patient_group_ref", "correctness_target", "raw_observations", "protected_test_rows"):
        assert forbidden not in serialized
    for synthetic_group in ("g1", "g2", "g3", "g4", "t1", "t2", "t3", "t4", "opaque-"):
        assert synthetic_group not in serialized
    assert artifact.lifecycle == "uncalibrated_non_deployable"
    with pytest.raises(TypeError):
        artifact.feature_schema["columns"][0]["name"] = "changed"
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        artifact.family = "other"


def test_artifact_safe_loader_requires_exact_compatibility_and_independent_origin(registered_collection):
    from safira.training.artifacts import ArtifactCompatibility, ArtifactOriginCheck, validate_artifact
    from safira.training.exceptions import TrainingArtifactError
    artifact = _artifact(registered_collection)
    payload = artifact.to_dict()
    compatibility = ArtifactCompatibility(
        artifact.scope.source_key, artifact.artifact_version, artifact.scope.classifier_artifact_sha256,
        artifact.scope.adapter_id, artifact.scope.adapter_version, artifact.scope.adapter_fingerprint,
        artifact.scope.preprocessing_identity, dict(artifact.training_protocol), dict(artifact.dataset_reference),
        dict(artifact.signal_run_reference), artifact.digest,
        _digest(artifact.to_dict()["feature_schema"]), _digest(artifact.to_dict()["preprocessing"]),
    )
    class Origin:
        def verify_artifact(self, submitted_digest, expected_scope, artifact_version):
            if submitted_digest != artifact.digest:
                return None
            return ArtifactOriginCheck(submitted_digest, expected_scope, artifact_version,
                                       "synthetic-custodian", "ledger-lookup", "synthetic-evidence")
    loaded = validate_artifact(payload, compatibility, Origin())
    assert loaded.digest == artifact.digest
    wrong = ArtifactCompatibility((artifact.scope.model_id, "v2", artifact.scope.label_id),
        artifact.artifact_version, artifact.scope.classifier_artifact_sha256, artifact.scope.adapter_id,
        artifact.scope.adapter_version, artifact.scope.adapter_fingerprint, artifact.scope.preprocessing_identity,
        dict(artifact.training_protocol), dict(artifact.dataset_reference), dict(artifact.signal_run_reference), artifact.digest,
        _digest(artifact.to_dict()["feature_schema"]), _digest(artifact.to_dict()["preprocessing"]))
    with pytest.raises(TrainingArtifactError):
        validate_artifact(payload, wrong, Origin())
    class AssertionOnly:
        def verify_artifact(self, *_):
            return True
    with pytest.raises(TrainingArtifactError):
        validate_artifact(payload, compatibility, AssertionOnly())
    class MismatchedOrigin:
        def verify_artifact(self, submitted_digest, expected_scope, artifact_version):
            return ArtifactOriginCheck("0" * 64, expected_scope, artifact_version,
                                       "synthetic-custodian", "ledger-lookup", "synthetic-evidence")
    with pytest.raises(TrainingArtifactError):
        validate_artifact(payload, compatibility, MismatchedOrigin())


def test_artifact_loader_rejects_dataset_method_schema_and_preprocessing_mismatches(registered_collection):
    from safira.training.artifacts import ArtifactCompatibility, ArtifactOriginCheck, validate_artifact
    from safira.training.exceptions import TrainingArtifactError
    artifact = _artifact(registered_collection)
    base = ArtifactCompatibility(
        artifact.scope.source_key, artifact.artifact_version, artifact.scope.classifier_artifact_sha256,
        artifact.scope.adapter_id, artifact.scope.adapter_version, artifact.scope.adapter_fingerprint,
        artifact.scope.preprocessing_identity, dict(artifact.training_protocol), dict(artifact.dataset_reference),
        dict(artifact.signal_run_reference), artifact.digest,
        _digest(artifact.to_dict()["feature_schema"]), _digest(artifact.to_dict()["preprocessing"]))
    class Origin:
        def verify_artifact(self, digest, scope, version):
            return ArtifactOriginCheck(digest, scope, version, "custodian", "ledger lookup", "receipt")
    changed_dataset = dict(base.dataset_reference)
    changed_dataset["manifest_digest"] = "0" * 64
    changed_run = dict(base.signal_run_reference)
    changed_run["method_ids"] = (("different", "v9", "{}"),)
    cases = (
        replace(base, dataset_reference=changed_dataset),
        replace(base, signal_run_reference=changed_run),
        replace(base, training_protocol={**dict(base.training_protocol), "version": "stale"}),
        replace(base, feature_schema_digest="0" * 64),
        replace(base, preprocessing_digest="0" * 64),
        replace(base, adapter_version="different"),
        replace(base, classifier_artifact_sha256="0" * 64),
        replace(base, scope_key=(artifact.scope.model_id, artifact.scope.model_version, "other-label")),
    )
    for expected in cases:
        with pytest.raises(TrainingArtifactError):
            validate_artifact(artifact.to_dict(), expected, Origin())


def test_artifact_loader_rejects_wrong_dimensions_even_with_recomputed_digest(registered_collection):
    from safira.training.artifacts import ArtifactCompatibility, ArtifactOriginCheck, validate_artifact
    from safira.training.exceptions import TrainingArtifactError
    artifact = _artifact(registered_collection)
    compatibility = ArtifactCompatibility(
        artifact.scope.source_key, artifact.artifact_version, artifact.scope.classifier_artifact_sha256,
        artifact.scope.adapter_id, artifact.scope.adapter_version, artifact.scope.adapter_fingerprint,
        artifact.scope.preprocessing_identity, dict(artifact.training_protocol), dict(artifact.dataset_reference), dict(artifact.signal_run_reference),
        artifact.digest, _digest(artifact.to_dict()["feature_schema"]), _digest(artifact.to_dict()["preprocessing"]))
    payload = artifact.to_dict()
    payload["estimator_state"]["coefficients"] = []
    import hashlib
    payload["digest"] = hashlib.sha256(json.dumps(
        {key: value for key, value in payload.items() if key != "digest"}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    class Origin:
        def verify_artifact(self, digest, scope, version):
            return ArtifactOriginCheck(digest, scope, version, "custodian", "ledger lookup", "receipt")
    with pytest.raises(TrainingArtifactError):
        validate_artifact(payload, compatibility, Origin())


def test_test_only_frozen_numerical_reproduction_and_baseline_constant(registered_collection):
    from safira.training.artifacts import _reproduce_probability_for_test
    from safira.training.exceptions import TrainingArtifactError
    from sklearn.linear_model import LogisticRegression
    from test_training_acceptance import _make_service
    registry, dataset, signals, protocol, _, service = _make_service(registered_collection)
    artifact = service.train(dataset, signals)[0].artifact
    if artifact.family == "l2_logistic":
        train_rows = tuple(row for row in dataset.development.train
                           if tuple(row.prediction.source_key) == artifact.scope.source_key)
        by_key = {row.row_key.value: row for row in signals.training}
        from safira.training.service import SafetyTrainingService
        features = tuple(by_key[service._row_key(dataset, signals, row)] for row in train_rows)
        from safira.training.features import build_feature_schema, fit_preprocessing, transform_rows
        schema = build_feature_schema(protocol, artifact.scope, features)
        prep = fit_preprocessing(protocol, schema, features)
        matrix = transform_rows(prep, schema, features)
        targets = tuple(row.correctness_target for row in train_rows)
        sklearn_model = LogisticRegression(penalty="l2", solver="lbfgs", C=1.0, tol=1e-4,
            max_iter=200, class_weight=None, fit_intercept=True, warm_start=False,
            random_state=None).fit(matrix, targets)
        reconstructed = _reproduce_probability_for_test(artifact, matrix[0])
        assert reconstructed == pytest.approx(sklearn_model.predict_proba((matrix[0],))[0][1], abs=1e-12)
    else:
        assert artifact.estimator_state["probability"] == pytest.approx(sum(
            row.correctness_target for row in dataset.development.train) / len(dataset.development.train))
        with pytest.raises(TrainingArtifactError):
            _reproduce_probability_for_test(artifact, (0.75,))

