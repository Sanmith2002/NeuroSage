"""Pure exact-registration and leakage validation helpers."""

from collections.abc import Mapping
from datetime import datetime
from .exceptions import DatasetCompatibilityError, DatasetLeakageError


def exact_label(registry, prediction):
    try:
        metadata = registry.get_metadata(prediction.model_id, prediction.model_version)
        label = next(item for item in metadata.labels if item.label_id == prediction.label_id)
    except Exception:
        raise DatasetCompatibilityError("registration_or_label_unavailable") from None
    return metadata, label


def validate_binding(target, binding, prediction, label):
    if binding.source_key != prediction.source_key or (binding.target_id,binding.target_version) != (target.target_id,target.target_version):
        raise DatasetCompatibilityError("target_binding_mismatch")
    if (binding.target_positive_to_label_class,binding.target_negative_to_label_class) != (label.positive_outcome,label.negative_outcome):
        raise DatasetCompatibilityError("target_semantics_mismatch")


def correctness(prediction, outcome, target, binding):
    if type(outcome) is not int or outcome not in (0,1):
        raise DatasetCompatibilityError("binary_outcome_required")
    mapped = binding.target_positive_to_label_class if outcome == 1 else binding.target_negative_to_label_class
    return int(prediction.primary.predicted_class == mapped)


def validate_transformations(declarations, held_out_groups, *, source_key=None, registered_identity=None):
    for declaration in declarations:
        get=declaration.get if isinstance(declaration,Mapping) else lambda key,default=None:getattr(declaration,key,default)
        if source_key is not None and get("source_key") not in (None,source_key):
            continue
        if set(get("fitted_on_groups", ())) & set(held_out_groups):
            raise DatasetLeakageError("held_out_transform_fit")
        expected=registered_identity if registered_identity is not None else get("expected_preprocessing_identity")
        if get("preprocessing_identity") != expected:
            raise DatasetLeakageError("preprocessing_identity_mismatch")


def validate_timing(prediction, declarations, *, required_categories=()):
    matched=[item for item in declarations if item.source_key==prediction.source_key and item.occurrence_ref==prediction.association.occurrence_ref]
    by_category={item.category:item for item in matched}
    if any(category not in by_category for category in required_categories):
        raise DatasetLeakageError("prediction_time_evidence_missing")
    prediction_time=prediction.provenance.details.get("predicted_at")
    for item in matched:
        if item.state!="verified" or item.category in {"outcome","correctness","patient_group","partition_role","verification"}:
            raise DatasetLeakageError("prediction_time_evidence_invalid")
        if not prediction_time:
            raise DatasetLeakageError("post_prediction_evidence")
        try:
            available=datetime.fromisoformat(item.available_at.replace("Z","+00:00"))
            predicted=datetime.fromisoformat(prediction_time.replace("Z","+00:00"))
            if available.tzinfo is None or predicted.tzinfo is None or available>predicted:
                raise ValueError
        except Exception:
            raise DatasetLeakageError("prediction_time_invalid") from None


def validate_predictor_separation(fields):
    prohibited={"outcome","ground_truth","correctness_target","patient_group_ref","partition_role","verification"}
    if prohibited.intersection(fields):
        raise DatasetLeakageError("outcome_derived_predictor")


def validate_prediction_provenance(prediction):
    provenance=prediction.provenance
    if provenance.source_key!=prediction.source_key or provenance.association!=prediction.association:
        raise DatasetCompatibilityError("prediction_provenance_mismatch")
    details=provenance.details
    if provenance.mode=="live":
        valid=provenance.assurance=="verified_live_binding" and all(type(details.get(key)) is str and details.get(key) for key in ("classifier_sha256","adapter_id","adapter_version","adapter_fingerprint","identity_scope")) and "output_selector" in details
    elif provenance.mode=="precomputed":
        valid=provenance.assurance=="trusted_source_checked" and all(details.get(key) is True for key in ("content_bound","association_bound","fresh","not_revoked","unused")) and all(type(details.get(key)) is str and details.get(key) for key in ("source_contract_id","source_contract_version","integration_id","independent_evidence_ref","event_id"))
    else:
        valid=False
    if not valid: raise DatasetCompatibilityError("prediction_provenance_unverified")
