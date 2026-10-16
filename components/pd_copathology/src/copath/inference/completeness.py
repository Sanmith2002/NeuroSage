"""Data completeness of a supplied record, computed BEFORE any imputation."""

from __future__ import annotations

from .schema import SIGNAL_NAMES


def completeness(observed: set[str], signal_features: dict[str, list[str]], modality: dict[str, str], n_unrecognised: int) -> dict:
    """Overall, per-modality and per-signal observed fractions. ``observed`` = supplied, non-null, valid features."""
    expected = list(dict.fromkeys(f for signal in SIGNAL_NAMES for f in signal_features[signal]))
    seen = [f for f in expected if f in observed]
    by_modality: dict[str, list[str]] = {}
    for feature in expected:
        by_modality.setdefault(modality.get(feature, "unclassified"), []).append(feature)
    fractions = {m: round(sum(f in observed for f in names) / len(names), 6) for m, names in sorted(by_modality.items())}
    return {
        "n_features_expected": len(expected), "n_features_observed": len(seen),
        "feature_completeness": round(len(seen) / len(expected), 6) if expected else 0.0,
        "available_modalities": [m for m, v in fractions.items() if v > 0],
        "missing_modalities": [m for m, v in fractions.items() if v == 0],
        "modality_completeness": fractions,
        "per_signal_completeness": {s: round(sum(f in observed for f in signal_features[s]) / len(signal_features[s]), 6)
                                    if signal_features[s] else 0.0 for s in SIGNAL_NAMES},
        "n_unrecognised_fields": int(n_unrecognised)}
