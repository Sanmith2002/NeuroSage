"""Input and output contracts of the frozen inference package (version 1.0).

* :func:`parse_record` - STRICT validation of one raw participant feature record.
* :func:`output_schema` / :func:`input_schema` - the JSON Schemas that are written to ``docs/``.
* :func:`validate_output` - validate a result against the output schema.

Nothing here reads data or a model.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

SCHEMA_VERSION = "1.0"
SIGNAL_NAMES = ("pd_type", "ad_like", "vascular_risk")
COHORTS = ("PD", "HC", "Prodromal", "SWEDD")
METADATA_FIELDS = ("participant_id", "cohort")
TBD = "TBD — student to complete"
CONTRACT_SOURCE = ("The v1 inference input contract reflects the raw pre-pipeline feature union of the frozen final model bundle. "
                   "It is intentionally not identical to the broader modelling-tier candidate feature configuration.")
SHAP_EXPLAINS = "uncalibrated model output (not the calibrated probability); contributions do not sum to the probability"
DISCLAIMER = ("Research proxy signals for co-pathology estimation. Not a clinical diagnosis. Reliability, out-of-distribution and "
              "TRUST/CAUTION/DEFER decisions are made by the downstream Clinical Predictive Safety Framework.")
# No output KEY or enumerated value may look like a decision that belongs to the downstream Safety Framework.
FORBIDDEN_RE = re.compile(r"(?i)(?<![a-z])(ood|trust|caution|defer|diagnosis|recommendation)(?![a-z])")

# Which cohorts each signal was trained on (targets/*.yaml, eligible_population). Never inferred from features.
COHORT_SCOPE = {"pd_type": {"PD", "HC"}, "ad_like": set(COHORTS), "vascular_risk": set(COHORTS)}


class InputValidationError(ValueError):
    """A supplied field cannot be parsed. Names the fields, never their values."""

    def __init__(self, fields: list[str], message: str):
        super().__init__(message)
        self.fields = fields


@dataclass
class ParsedRecord:
    participant_id: str | None
    cohort: str | None
    values: dict[str, float] = field(default_factory=dict)  # OBSERVED features only (supplied, non-null, valid)
    n_unrecognised_fields: int = 0


def _number(value) -> float | None:
    """A finite float, or None for an absent value. Raises ValueError for anything that is not a clean number."""
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("boolean")
    if isinstance(value, (int, np.integer)):
        return float(value)
    if isinstance(value, (float, np.floating)):
        if math.isnan(value):
            return None  # a missing cell of a table
        if math.isinf(value):
            raise ValueError("infinite")
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        number = float(text)  # ValueError for anything that is not numeric text
        if not math.isfinite(number):
            raise ValueError("not finite")
        return number
    raise ValueError("type")


def parse_record(record: Mapping, features: list[str]) -> ParsedRecord:
    """Validate one raw record against the feature names the frozen pipelines use.

    Extra fields are ignored and counted (their names are never echoed). A supplied value that is not a number is a
    validation error naming the field; it is never turned into a missing value. Explicit null / empty counts as absent.
    """
    if not isinstance(record, Mapping):
        raise InputValidationError([], "a record must be a mapping of field names to values")
    known, bad, values = set(features), [], {}
    for name, value in record.items():
        if name in METADATA_FIELDS:
            continue
        if name not in known:
            continue
        try:
            number = _number(value)
        except (ValueError, TypeError):
            bad.append(str(name))
            continue
        if number is not None:
            values[name] = number
    cohort_raw, cohort = record.get("cohort"), None
    if cohort_raw is not None and not (isinstance(cohort_raw, float) and math.isnan(cohort_raw)) and str(cohort_raw).strip() != "":
        matches = [c for c in COHORTS if str(cohort_raw).strip().lower() == c.lower()]
        if not matches:
            bad.append("cohort")
        else:
            cohort = matches[0]
    if bad:
        raise InputValidationError(sorted(bad), f"input validation failed for field(s): {', '.join(sorted(bad))} "
                                               "(not parseable as the declared type; values are not shown)")
    pid = record.get("participant_id")
    pid = None if pid is None or (isinstance(pid, float) and math.isnan(pid)) or str(pid).strip() == "" else str(pid).strip()
    unrecognised = sum(1 for name in record if name not in known and name not in METADATA_FIELDS)
    return ParsedRecord(pid, cohort, values, unrecognised)


# --------------------------------------------------------------------------
# JSON Schemas
# --------------------------------------------------------------------------

def _unit(description: str) -> dict:
    return {"type": "number", "minimum": 0, "maximum": 1, "description": description}


def output_schema() -> dict:
    top_feature = {"type": "object", "additionalProperties": False, "required": ["feature", "modality", "shap", "direction"],
                   "properties": {"feature": {"type": "string"}, "modality": {"type": "string"}, "shap": {"type": "number"},
                                  "direction": {"enum": ["increases", "decreases"]}}}
    signal = {"type": "object", "additionalProperties": False,
              "required": ["probability", "model", "calibration", "target_definition", "cohort_in_training_scope", "shap_space",
                           "shap_explains", "top_features"],
              "properties": {"probability": _unit("Calibrated probability of the research proxy signal."), "model": {"type": "string"},
                             "calibration": {"type": "string"}, "target_definition": {"type": "string"},
                             "cohort_in_training_scope": {"type": ["boolean", "null"]}, "shap_space": {"type": "string"},
                             "shap_explains": {"type": "string"},
                             "top_features": {"type": "array", "maxItems": 5, "items": top_feature}}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "pd-copathology-output-schema-v1.0.json",
        "title": "PD co-pathology signal estimation: inference output, schema version 1.0", "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "participant_id", "model_version", "selected_models_sha256", "generated_at", "signals",
                     "data_quality", "disclaimer"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION}, "participant_id": {"type": ["string", "null"]},
            "model_version": {"type": "string"}, "selected_models_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "generated_at": {"type": "string", "format": "date-time", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"},
            "signals": {"type": "object", "additionalProperties": False, "required": list(SIGNAL_NAMES),
                        "properties": {name: signal for name in SIGNAL_NAMES}},
            "data_quality": {"type": "object", "additionalProperties": False,
                             "required": ["n_features_expected", "n_features_observed", "feature_completeness", "available_modalities",
                                          "missing_modalities", "modality_completeness", "per_signal_completeness", "n_unrecognised_fields"],
                             "properties": {
                                 "n_features_expected": {"type": "integer", "minimum": 0},
                                 "n_features_observed": {"type": "integer", "minimum": 0},
                                 "feature_completeness": _unit("Observed fraction of the expected raw features, before any imputation."),
                                 "available_modalities": {"type": "array", "items": {"type": "string"}},
                                 "missing_modalities": {"type": "array", "items": {"type": "string"}},
                                 "modality_completeness": {"type": "object", "additionalProperties": _unit("Observed fraction of the modality's features.")},
                                 "per_signal_completeness": {"type": "object", "additionalProperties": False, "required": list(SIGNAL_NAMES),
                                                             "properties": {name: _unit("Observed fraction of this signal's features.") for name in SIGNAL_NAMES}},
                                 "n_unrecognised_fields": {"type": "integer", "minimum": 0}}},
            "disclaimer": {"const": DISCLAIMER}}}


def input_schema(features: dict[str, dict], source: str = CONTRACT_SOURCE) -> dict:
    """JSON Schema of an input record. ``features`` maps a raw feature name to ``{"modality": ..., "signals": [...]}``.

    The ORDER of ``features`` is the canonical feature sequence; it is stored explicitly in ``x-feature-order`` (the order of the
    JSON object keys is not the definition). ``source`` states where the feature list comes from.
    """
    properties = {
        "participant_id": {"type": ["string", "integer", "null"], "description": "Caller's (pseudonymous) identifier; echoed in the output; not a model feature."},
        "cohort": {"enum": [*COHORTS, None], "description": "Optional enrolment cohort. Used only for cohort_in_training_scope; never a model feature."}}
    for name, meta in features.items():
        properties[name] = {"type": ["number", "null"], "description": meta.get("description", TBD), "x-modality": meta["modality"],
                            "x-signals": list(meta["signals"])}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "pd-copathology-input-schema-v1.0.json",
        "title": "PD co-pathology signal estimation: raw participant feature record, schema version 1.0", "type": "object",
        "description": ("One participant's baseline features before any pipeline step. Absent or null features are handled only by the frozen "
                        "pipeline. Unknown fields are ignored and counted (n_unrecognised_fields). A supplied value that is not a number is "
                        "a validation error."),
        "x-contract-source": source, "x-feature-order": list(features),
        "properties": properties, "additionalProperties": True}


def validate_output(result: dict) -> None:
    import jsonschema

    jsonschema.Draft202012Validator(output_schema()).validate(result)
    found = _forbidden_names(result)
    if found:
        raise ValueError(f"the output contains a key or enumerated value reserved for the downstream Safety Framework: {found}")


def _forbidden_names(node, path: str = "") -> list[str]:
    """Keys and short enumerated string values (never the disclaimer or free text) that match a reserved word."""
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if FORBIDDEN_RE.search(str(key)):
                hits.append(f"{path}/{key}")
            if key not in ("disclaimer", "participant_id"):
                hits += _forbidden_names(value, f"{path}/{key}")
    elif isinstance(node, list):
        for item in node:
            hits += _forbidden_names(item, path)
    elif isinstance(node, str) and len(node) <= 24 and FORBIDDEN_RE.search(node):
        hits.append(f"{path} (value)")
    return hits
