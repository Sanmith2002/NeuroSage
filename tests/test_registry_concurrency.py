"""T013/T015: two independent connections contend for one immutable exact key."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3
from threading import Barrier

import pytest

from conftest import SyntheticIdentityProvider
from safira.registry import (
    DuplicateRegistrationError,
    ModelRegistry,
    RegisteredModelVersion,
    UnattachedModelError,
)


@pytest.mark.parametrize("different_metadata", [False, True])
def test_concurrent_duplicate_registration_commits_once_and_preserves_winner(
    catalog_path, synthetic_metadata, synthetic_classifier_artifact, different_metadata
):
    # Storage initialization is foundational; the tested race is registration.
    with ModelRegistry(catalog_path):
        pass
    barrier = Barrier(2)

    def compete(index):
        provider = SyntheticIdentityProvider(synthetic_classifier_artifact)
        record = deepcopy(synthetic_metadata)
        if different_metadata:
            record["preprocessing_identity"] = f"synthetic-transform-{index}"
        declared = RegisteredModelVersion.from_dict(record)
        with ModelRegistry(catalog_path) as registry:
            barrier.wait(timeout=10)
            try:
                registry.register(declared, provider.classifier, provider.adapter, provider)
            except DuplicateRegistrationError:
                with pytest.raises(UnattachedModelError):
                    registry.resolve_usable(declared.model_id, declared.model_version)
                return "duplicate", registry.get_metadata(
                    declared.model_id, declared.model_version
                ).to_dict()
            assert registry.resolve_usable(
                declared.model_id, declared.model_version
            ).classifier is provider.classifier
            assert registry.get_metadata(declared.model_id, declared.model_version) == declared
            return "accepted", declared.to_dict()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(compete, index) for index in range(2)]
        outcomes = [future.result(timeout=20) for future in futures]
    assert sorted(status for status, _ in outcomes) == ["accepted", "duplicate"]
    winner = next(record for status, record in outcomes if status == "accepted")
    assert all(record == winner for _, record in outcomes)
    with ModelRegistry(catalog_path) as reopened:
        assert reopened.get_metadata("synthetic-model", "v1").to_dict() == winner
    with sqlite3.connect(catalog_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 1
