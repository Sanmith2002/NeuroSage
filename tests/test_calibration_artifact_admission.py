import pytest

from safira.calibration.verification import verify_estimator_artifact
from safira.training.artifacts import ArtifactOriginCheck
from test_training_acceptance import _make_service


class ArtifactLedger:
    def __init__(self):
        self.entries = set()

    def admit(self, artifact):
        self.entries.add((artifact.digest, artifact.scope.source_key, artifact.artifact_version))

    def verify_artifact(self, digest, scope, version):
        key = (digest, tuple(scope), version)
        if key not in self.entries:
            raise ValueError("not independently recorded")
        return ArtifactOriginCheck(digest, tuple(scope), version, "synthetic-ledger",
                                   "exact content lookup", "artifact-entry")


def test_selected_artifact_requires_independent_exact_origin(registered_collection):
    registry, dataset, signals, _, _, service = _make_service(registered_collection)
    artifact = service.train(dataset, signals)[0].artifact
    from safira.training.records import TrainingScope
    scope = artifact.scope
    ledger = ArtifactLedger()
    with pytest.raises(Exception):
        verify_estimator_artifact(registry, artifact, scope, ledger)
    ledger.admit(artifact)
    accepted = verify_estimator_artifact(registry, artifact, scope, ledger)
    assert accepted.digest == artifact.digest


def test_artifact_wrong_scope_digest_or_assertion_only_origin_is_rejected(registered_collection):
    registry, dataset, signals, _, _, service = _make_service(registered_collection)
    artifact = service.train(dataset, signals)[0].artifact
    ledger = ArtifactLedger()
    ledger.admit(artifact)
    from dataclasses import replace
    wrong_scope = replace(artifact.scope, model_version="v9")
    with pytest.raises(Exception):
        verify_estimator_artifact(registry, artifact, wrong_scope, ledger)

    class AssertionOnly:
        def verify_artifact(self, *_):
            return True
    with pytest.raises(Exception):
        verify_estimator_artifact(registry, artifact, artifact.scope, AssertionOnly())


@pytest.mark.parametrize("field,value", [
    ("classifier_artifact_sha256", "c" * 64),
    ("adapter_id", "wrong-adapter"),
    ("preprocessing_identity", "wrong-preprocessing"),
])
def test_artifact_registration_adapter_and_preprocessing_identity_are_exact(
        registered_collection, field, value):
    from dataclasses import replace
    registry, dataset, signals, _, _, service = _make_service(registered_collection)
    artifact = service.train(dataset, signals)[0].artifact
    ledger = ArtifactLedger()
    ledger.admit(artifact)
    bad_scope = replace(artifact.scope, **{field: value})
    with pytest.raises(Exception):
        verify_estimator_artifact(registry, artifact, bad_scope, ledger)
