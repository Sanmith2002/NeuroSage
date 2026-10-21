"""Stable privacy-safe Feature 005 errors."""

_SAFE_CODES = frozenset({
    "training_error", "training_configuration_invalid", "signal_feature_set_invalid",
    "correctness_example_invalid", "dataset_reference_invalid", "feature_set_not_canonical",
    "input_not_canonical", "partition_role_mismatch", "source_record_invalid", "source_scope_invalid",
    "training_input_type_invalid", "dataset_feature_scope_mismatch", "dataset_manifest_mismatch",
    "dataset_not_ready", "dataset_row_duplicate", "feature_row_duplicate",
    "feature_row_inventory_mismatch", "feature_row_missing", "feature_source_mismatch",
    "input_check_invalid", "input_evidence_mismatch", "input_verification_failed",
    "manifest_digest_unverified", "predictor_source_mismatch", "source_admission_rejected",
    "trusted_verifier_required", "fitted_reference_mismatch", "fitted_reference_preprocessing_mismatch",
    "fitted_reference_registration_missing", "signal_method_duplicate", "signal_method_mismatch",
    "signal_protocol_incompatible", "source_outside_training_protocol", "scope_protocol_incomplete",
    "registration_not_found", "registered_scope_identity_mismatch", "registered_prediction_incompatible",
    "patient_group_support_insufficient", "correctness_class_support_insufficient",
    "aligned_training_features_unavailable", "signal_input_invalid", "signal_provenance_not_ready",
    "required_signal_unavailable", "training_rows_unavailable",
    "selection_protocol_not_ready", "selection_criteria_not_ready", "validation_inventory_invalid",
    "validation_matrix_invalid", "candidate_scope_mismatch", "validation_class_support_insufficient",
    "candidate_failure_policy_blocked", "candidate_not_comparable", "candidate_probability_invalid",
    "artifact_payload_invalid", "artifact_schema_invalid", "artifact_preprocessing_invalid",
    "artifact_estimator_invalid", "artifact_digest_invalid", "artifact_incompatible",
    "artifact_origin_not_ready", "artifact_origin_rejected", "artifact_reproduction_unavailable",
    "artifact_reproduction_shape_invalid", "artifact_reproduction_invalid", "training_scope_not_ready",
    "training_features_invalid", "training_candidate_failed", "training_comparison_undefined",
})


class TrainingError(Exception):
    def __init__(self, code: str):
        self.code = code if type(code) is str and code in _SAFE_CODES else "training_error"
        super().__init__(self.code)


class TrainingInputError(TrainingError):
    pass


class TrainingVerificationError(TrainingError):
    pass


class TrainingCompatibilityError(TrainingError):
    pass


class TrainingArtifactError(TrainingError):
    pass
