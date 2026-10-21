"""Allowlisted integrity and exact-compatibility checks for calibrator records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from safira.calibration.records import CalibratorArtifact


_COMPATIBILITY_FIELDS = frozenset({
    "scope", "base_artifact_digest", "base_artifact_version", "base_family",
    "base_feature_schema_digest", "base_preprocessing_digest", "dataset_reference",
    "signal_run_reference", "calibration_protocol", "method_id", "method_version",
})


def _plain(value):
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _canonical(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def export_calibrator_artifact(artifact: CalibratorArtifact) -> dict:
    """Return detached, allowlisted JSON-compatible artifact content.

    This operation provides neither origin authentication nor durable storage.
    """
    if type(artifact) is not CalibratorArtifact:
        raise ValueError("artifact_invalid")
    try:
        payload = artifact.to_dict()
        json.loads(_canonical(payload))
        return payload
    except Exception:
        raise ValueError("artifact_invalid") from None


def validate_calibrator_artifact(payload: Mapping, *, expected: Mapping | None = None) -> CalibratorArtifact:
    """Validate canonical content and explicitly supplied compatibility fields.

    A valid digest detects content change. It does not establish who created the
    record or whether it has been persisted.
    """
    try:
        artifact = CalibratorArtifact.from_dict(payload)
        body = {key: value for key, value in dict(payload).items() if key != "digest"}
        digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        if digest != artifact.digest:
            raise ValueError
        if expected is not None:
            if not isinstance(expected, Mapping) or not set(expected) <= _COMPATIBILITY_FIELDS:
                raise ValueError
            actual = artifact.to_dict()
            for key, value in expected.items():
                if _canonical(actual[key]) != _canonical(value.to_dict() if key == "scope" and hasattr(value, "to_dict") else value):
                    raise ValueError
        return artifact
    except Exception:
        raise ValueError("artifact_compatibility_rejected") from None
