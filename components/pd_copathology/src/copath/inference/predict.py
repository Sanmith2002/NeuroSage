"""Frozen-model inference: one record (or a batch) -> three calibrated probabilities, explanations and completeness.

Nothing is persisted. The bundle must already be verified (see :func:`copath.inference.bundle.load_bundle`); no function here
fits, tunes, calibrates or thresholds anything.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from .bundle import Bundle
from .completeness import completeness
from .explanations import top_features
from .schema import COHORT_SCOPE, DISCLAIMER, SCHEMA_VERSION, SHAP_EXPLAINS, SIGNAL_NAMES, InputValidationError, ParsedRecord, parse_record


def _frame(model, parsed: ParsedRecord) -> pd.DataFrame:
    """One row in the frozen feature order; absent features are NaN and are handled only by the frozen pipeline."""
    return pd.DataFrame([[parsed.values.get(f, np.nan) for f in model.features]], columns=model.features, dtype=float)


def predict_record(bundle: Bundle, record: Mapping, generated_at: str | None = None) -> dict:
    parsed = parse_record(record, bundle.features)
    observed = set(parsed.values)
    signals = {}
    for name in SIGNAL_NAMES:
        model = bundle.signals[name]
        X = _frame(model, parsed)
        probability = float(model.calibrator.predict_proba(X)[0, 1])
        if not 0.0 <= probability <= 1.0:
            raise ValueError(f"{name}: the calibrated probability is outside [0, 1]")
        explained = model.explainer.explain(X)
        signals[name] = {
            "probability": probability, "model": model.family, "calibration": model.calibration, "target_definition": model.label,
            "cohort_in_training_scope": None if parsed.cohort is None else parsed.cohort in COHORT_SCOPE[name],
            "shap_space": model.explainer.space,
            "shap_explains": SHAP_EXPLAINS,
            "top_features": top_features(explained["contributions"], model.features, observed, bundle.modality)}
    return {"schema_version": SCHEMA_VERSION, "participant_id": parsed.participant_id, "model_version": bundle.model_version,
            "selected_models_sha256": bundle.selected_models_sha256,
            "generated_at": generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "signals": signals,
            "data_quality": completeness(observed, bundle.signal_features, bundle.modality, parsed.n_unrecognised_fields),
            "disclaimer": DISCLAIMER}


def predict_batch(bundle: Bundle, records: Iterable[Mapping]) -> list[dict]:
    """One result per record, in order. Nothing is persisted. An invalid record stops the batch and is named by its position."""
    results = []
    for i, record in enumerate(records):
        try:
            results.append(predict_record(bundle, record))
        except InputValidationError as exc:
            raise InputValidationError(exc.fields, f"record {i}: {exc}") from None
    return results
