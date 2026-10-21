"""Atomic cohort-only Feature 007 policy selection service."""

from __future__ import annotations

from hashlib import sha256
import json
from types import MappingProxyType

from safira.dataset.records import DatasetBuildResult
from safira.policy.exceptions import PolicyInputError, PolicyVerificationError
from safira.policy.artifacts import freeze_policy_artifact
from safira.policy.records import (PolicyEvidenceReference, PolicyScope,
    PolicySelectionOutcome, PolicySelectionProtocol, PolicySelectionSummary,
    PolicyStatus, SelectivePolicyArtifact)
from safira.policy.references import reconstruct_original_references
from safira.policy.scoring import reconstruct_calibrated_scores
from safira.policy.selection import _choose_cutoff, _index_assessments
from safira.policy.signals import build_policy_signal_rows
from safira.policy.verification import (_verify_dataset, _verify_targets,
    verify_artifact_bundle, verify_patient_disjointness, verify_protocol_approval)


def _feature003_reference(values):
    from safira.signals.records import Feature003DatasetReference
    return Feature003DatasetReference(values["dataset_id"], values["protocol_id"],
        values["protocol_version"], values["manifest_reference"], values["builder_version"],
        values["manifest_digest"])


def _validate_artifact_bindings(estimator, calibrator, dataset, reference, signals):
    from safira.training.verification import _inventory, _methods, feature_set_fingerprint
    from safira.signals.validation import dataset_fingerprint

    dataset_ref = estimator.dataset_reference
    signal_ref = estimator.signal_run_reference
    expected_ref = {"dataset_id": reference.dataset_id, "manifest_reference": reference.manifest_reference,
        "manifest_digest": reference.manifest_digest, "protocol_id": reference.protocol_id,
        "protocol_version": reference.protocol_version, "builder_version": reference.builder_version}
    if any(dataset_ref[name] != value for name, value in expected_ref.items()):
        raise PolicyVerificationError("scope_incompatible")
    methods = tuple(sorted((item.method_id, item.method_version,
        sha256(json.dumps(item.to_dict()["parameters"], sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode()).hexdigest())
        for item in signals.manifest.method_configs))
    states = tuple(sorted(state.state_id for state in signals.manifest.fitted_state_references))
    expected_inventory = sha256(json.dumps(
        _inventory(dataset, signals, reference), sort_keys=True, separators=(",", ":"),
        default=list).encode()).hexdigest()
    if (signal_ref["run_version"] != signals.manifest.run_version
            or signal_ref["feature_set_fingerprint"] != feature_set_fingerprint(signals)
            or tuple(tuple(item) for item in signal_ref["method_ids"]) != methods
            or tuple(signal_ref["fitted_state_ids"]) != states
            or tuple(signal_ref["scope_key"]) != estimator.scope.source_key
            or dataset_ref["dataset_fingerprint"] != dataset_fingerprint(dataset)):
        raise PolicyVerificationError("scope_incompatible")
    if dataset_ref["admitted_inventory_digest"] != expected_inventory:
        raise PolicyVerificationError("scope_incompatible")
    if calibrator.dataset_reference["inventory_digest"] != expected_inventory:
        raise PolicyVerificationError("scope_incompatible")
    if calibrator.base_preprocessing_digest != sha256(json.dumps(
            estimator.to_dict()["preprocessing"], sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest():
        raise PolicyVerificationError("scope_incompatible")


class PolicySelectionService:
    """Select and freeze aggregate policy outcomes; never score patients publicly."""

    def __init__(self, registry, protocol: PolicySelectionProtocol, input_verifier):
        if (registry is None or type(protocol) is not PolicySelectionProtocol
                or input_verifier is None):
            raise PolicyInputError("input_invalid")
        self._registry = registry
        self._protocol = protocol
        self._input_verifier = input_verifier

    def select(self, *, policy_dataset: DatasetBuildResult,
               original_training_dataset: DatasetBuildResult,
               original_signal_protocol, estimator_artifacts, calibrator_artifacts,
               prior_history=()):
        """Run the complete shared gate before any outcome-based selection work."""
        try:
            return self._select_verified(policy_dataset=policy_dataset,
                original_training_dataset=original_training_dataset,
                original_signal_protocol=original_signal_protocol,
                estimator_artifacts=estimator_artifacts,
                calibrator_artifacts=calibrator_artifacts, prior_history=prior_history)
        except (PolicyInputError, PolicyVerificationError):
            raise
        except Exception:
            raise PolicyVerificationError("verification_rejected") from None

    def _select_verified(self, *, policy_dataset, original_training_dataset,
                         original_signal_protocol, estimator_artifacts,
                         calibrator_artifacts, prior_history):
        from safira.signals.records import SignalProtocol, SignalSourceKey
        from safira.signals.service import SignalExtractor

        if (type(policy_dataset) is not DatasetBuildResult
                or type(original_training_dataset) is not DatasetBuildResult
                or type(original_signal_protocol) is not SignalProtocol
                or not isinstance(estimator_artifacts, dict)
                or not isinstance(calibrator_artifacts, dict)):
            raise PolicyInputError("input_invalid")
        verify_protocol_approval(self._input_verifier, self._protocol)

        # Successful artifacts expose aggregate selection results, so require
        # explicit protocol authorization before publishing them.
        if not self._protocol.disclose_support:
            return tuple(PolicySelectionOutcome(scope, PolicyStatus.NOT_READY,
                "aggregate_disclosure_not_authorized") for scope in self._protocol.scopes)

        scopes = tuple(self._protocol.scopes)
        by_source = {scope.source_key: scope for scope in scopes}
        expected_sources = set(by_source)
        estimator_map = dict(estimator_artifacts)
        calibrator_map = dict(calibrator_artifacts)
        if set(estimator_map) != expected_sources or set(calibrator_map) != expected_sources:
            raise PolicyVerificationError("inventory_mismatch")
        signal_sources = {item.to_tuple() for item in original_signal_protocol.source_keys}
        if (signal_sources != expected_sources
                or original_signal_protocol.protocol_id == ""
                or original_signal_protocol.protocol_version == ""):
            raise PolicyVerificationError("scope_incompatible")

        first_estimator = estimator_map[next(iter(sorted(expected_sources)))]
        original_reference = _feature003_reference(first_estimator.dataset_reference)
        if (original_signal_protocol.protocol_id != original_reference.protocol_id
                or original_signal_protocol.protocol_version != original_reference.protocol_version):
            raise PolicyVerificationError("scope_incompatible")
        for source in expected_sources:
            estimator, calibrator = estimator_map[source], calibrator_map[source]
            # Dataset identity must be shared, while each Feature 005 signal-run
            # reference is correctly bound to its own exact label scope.
            if estimator.dataset_reference != first_estimator.dataset_reference:
                raise PolicyVerificationError("scope_incompatible")
            verify_artifact_bundle(self._registry, by_source[source], estimator, calibrator,
                                   self._input_verifier)

        if (self._protocol.policy_evidence.dataset_id == original_reference.dataset_id
                or self._protocol.policy_evidence.manifest_digest == original_reference.manifest_digest):
            raise PolicyVerificationError("patient_overlap_detected")
        policy_reference = self._protocol.policy_evidence.to_feature003_reference()
        _verify_dataset(self._input_verifier, self._input_verifier,
                        original_training_dataset, original_reference, original_signal_protocol)
        policy_signal_protocol = SignalProtocol(policy_reference.protocol_id,
            policy_reference.protocol_version, original_signal_protocol.source_keys,
            original_signal_protocol.method_configs, original_signal_protocol.evidence_prerequisites,
            original_signal_protocol.cohort_adequacy)
        _verify_dataset(self._input_verifier, self._input_verifier,
                        policy_dataset, policy_reference, policy_signal_protocol)
        verify_patient_disjointness(self._input_verifier, policy_dataset,
            self._protocol.policy_evidence, original_reference, prior_history, scopes)
        # Ground-truth use begins only after protocol approval, exact inventories,
        # source admission and complete cross-source disjointness have passed.
        _verify_targets(self._input_verifier, original_training_dataset, self._protocol)
        _verify_targets(self._input_verifier, policy_dataset, self._protocol)

        extractor = SignalExtractor(self._registry, original_signal_protocol,
                                    self._input_verifier, dataset_verifier=self._input_verifier)
        original_signals = extractor.build_feature_set(original_training_dataset, original_reference)
        fitted_states = reconstruct_original_references(original_training_dataset,
            original_reference, original_signal_protocol, original_signals)
        for source in expected_sources:
            estimator, calibrator = estimator_map[source], calibrator_map[source]
            _validate_artifact_bindings(estimator, calibrator, original_training_dataset,
                                        original_reference, original_signals)

        policy_extractor = SignalExtractor(self._registry, policy_signal_protocol,
                                           self._input_verifier, dataset_verifier=self._input_verifier)
        policy_rows = build_policy_signal_rows(policy_dataset, policy_reference,
            policy_signal_protocol, policy_extractor, fitted_states, self._input_verifier)
        method_parameters = {method.method_id: method.parameters
                             for method in original_signal_protocol.method_configs.values()}
        outcomes = []
        by_row = {row.row_key.value: row for row in policy_rows}
        for scope in sorted(scopes, key=lambda item: item.source_key):
            source = scope.source_key
            examples = tuple(example for example in policy_dataset.development.validation
                             if tuple(example.prediction.source_key) == source)
            rows = tuple(by_row[_row_key(policy_reference, example.prediction)]
                         for example in examples)
            score_batch = reconstruct_calibrated_scores(estimator_map[source], calibrator_map[source],
                                                        rows, method_parameters)
            scores_by_key = dict(zip(score_batch.row_keys, score_batch.values))
            indexes = _index_assessments(examples, source)
            selected_scores, targets, groups = [], [], []
            for example in indexes:
                key = _row_key(policy_reference, example.prediction)
                if key not in scores_by_key:
                    raise PolicyVerificationError("inventory_mismatch")
                selected_scores.append(scores_by_key[key])
                targets.append(example.correctness_target)
                groups.append(example.patient_group_ref)
            result = _choose_cutoff(selected_scores, targets, groups, self._protocol, scope=scope)
            if result.status is not PolicyStatus.SELECTED_UNEVALUATED:
                outcomes.append(PolicySelectionOutcome(scope, result.status, result.reason_code))
                continue
            estimator, calibrator = estimator_map[source], calibrator_map[source]
            artifact = freeze_policy_artifact(scope=scope, protocol_id=self._protocol.protocol_id,
                protocol_version=self._protocol.version, protocol_digest=self._protocol.digest,
                estimator_digest=estimator.digest, calibrator_digest=calibrator.digest,
                original_dataset_reference=estimator.dataset_reference,
                original_signal_reference=estimator.signal_run_reference,
                policy_evidence=self._protocol.policy_evidence,
                selection_configuration={"risk_ceiling": self._protocol.risk_ceiling,
                    "candidate_cutoffs": self._protocol.candidate_cutoffs,
                    "target_bindings": {key: value for key, value in self._protocol.target_bindings.items()},
                    "minimum_eligible_patients": self._protocol.minimum_eligible_patients,
                    "minimum_selected_patients": self._protocol.minimum_selected_patients,
                    "correctness_support": {str(k): v for k, v in self._protocol.correctness_support.items()},
                    "comparison": self._protocol.comparison, "tie_rule": self._protocol.tie_rule,
                    "index_rule": self._protocol.index_rule, "valid_below_cutoff_status": "CAUTION",
                    "invalid_input_status": "DEFER"}, selection=result.summary)
            outcomes.append(PolicySelectionOutcome(scope, PolicyStatus.SELECTED_UNEVALUATED,
                                                  "selection_complete", artifact, result.summary))
        return tuple(outcomes)


def _row_key(reference, prediction):
    from safira.signals.validation import prediction_fingerprint
    from safira.signals.records import SignalRowKey
    material = f"{reference.dataset_id}\0{reference.manifest_reference}\0{prediction_fingerprint(prediction)}".encode()
    return SignalRowKey(sha256(material).hexdigest()).value

