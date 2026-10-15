"""Frozen-model inference package (Phase 4A). Verifies the frozen bundle, then maps one raw feature record to three research
proxy signals with local explanations and data-quality information. No training, tuning or calibration code is ever called."""

from .bundle import Bundle, BundleIntegrityError, load_bundle
from .explanations import AdditivityError, SpecError
from .predict import predict_batch, predict_record
from .schema import InputValidationError

__all__ = ["AdditivityError", "Bundle", "BundleIntegrityError", "InputValidationError", "SpecError", "load_bundle", "predict_batch",
           "predict_record"]
