"""A fully synthetic participant record to exercise the inference pipeline.

The values are fixed, deterministic placeholders computed from the feature NAME only (a checksum), not derived from any real
data or statistics. They are not meant to represent a real or clinically plausible participant.
"""

from __future__ import annotations

import zlib

DEMO_ID = "SYNTHETIC_DEMO_001"


def make_synthetic_record(features: dict[str, str], missing_modalities: tuple[str, ...] = (), cohort: str | None = None) -> dict:
    """``features`` maps each raw feature name to its modality; features of ``missing_modalities`` are left out."""
    record: dict = {"participant_id": DEMO_ID}
    if cohort:
        record["cohort"] = cohort
    for name, modality in features.items():
        if modality in missing_modalities:
            continue
        record[name] = round((zlib.crc32(name.encode("utf-8")) % 1000) / 100.0, 2)  # 0.00 .. 9.99, fixed per name
    return record
