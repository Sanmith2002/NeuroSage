"""Beginner-friendly synthetic demonstration of Safira Feature 002."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from safira.adapters import AdapterCapabilities, ModelAdapter
from safira.collection import (
    CollectionAssociation,
    ComponentContribution,
    LiveRequest,
    NormalizedEnvelope,
    OutputCandidate,
    PrecomputedCollector,
    SourceDeclarations,
    TrustedSourceIntegration,
    collect_live,
)
from safira.collection.exceptions import ProvenanceCheckFailed
from safira.collection.precomputed import ProvenanceCheck
from safira.registry import IdentityEvidence, ModelRegistry, RegisteredModelVersion


@dataclass(frozen=True)
class DemoClassifier:
    """Synthetic classifier identity; it contains no patient data."""

    artifact: bytes


class DemoAdapter(ModelAdapter):
    """Small deterministic model adapter used only by this demonstration."""

    implementation_artifact = b"safira-manual-collection-demo-adapter-v1"

    def __init__(self, classifier: DemoClassifier) -> None:
        super().__init__(AdapterCapabilities(
            prediction_probability=True,
            feature_representation=True,
            repeated_outputs=True,
            modality_outputs=True,
            domain_metadata=True,
            explanation=True,
            input_metadata=True,
            available_modalities=True,
        ))
        self.classifier = classifier

    def predict(self, patient_data, label):
        # Safira requires the base prediction method even when this registered
        # label uses predict_probability as its declared primary source.
        return "positive" if label == "synthetic-label" else "unknown"

    def predict_probability(self, patient_data, label):
        return 0.82

    def extract_features(self, patient_data, label):
        return [0.2, 0.4]

    def get_repeated_outputs(self, patient_data, label):
        return [0.79, 0.84]

    def get_modality_outputs(self, patient_data, label):
        return {"MRI": 0.80, "clinical": 0.77}

    def get_domain_metadata(self, patient_data):
        return {"cohort": "synthetic-demo", "cohort_in_training_scope": False}

    def explain(self, patient_data, label):
        return {"feature": "synthetic_feature", "attribution": 0.12}

    def get_input_metadata(self, patient_data):
        return {"completeness": "synthetic complete"}

    def get_available_modalities(self, patient_data):
        return ["MRI", "clinical"]


class DemoIdentityProvider:
    """Synthetic owner/loader that checks the actual pair used for registration."""

    def __init__(self, classifier: DemoClassifier, adapter: DemoAdapter) -> None:
        self.classifier = classifier
        self.adapter = adapter

    def identify_loaded_pair(self, classifier: object, adapter: ModelAdapter) -> IdentityEvidence:
        return IdentityEvidence(
            classifier_sha256=sha256(self.classifier.artifact).hexdigest(),
            adapter_sha256=sha256(self.adapter.implementation_artifact).hexdigest(),
            loaded_pair_verified=(classifier is self.classifier and adapter is self.adapter
                                  and self.adapter.classifier is self.classifier),
        )


class DemoSourceContract:
    """A tiny, explicitly versioned synthetic JSON source format."""

    contract_id = "safira-manual-demo-source"
    version = "1"

    def parse(self, raw_json: str | bytes) -> NormalizedEnvelope:
        document = json.loads(raw_json)
        if set(document) != {"schema", "result"} or document["schema"] != self.version:
            raise ValueError("Unsupported demo document")
        result = document["result"]
        if set(result) != {"output", "probability", "event"}:
            raise ValueError("Invalid demo result")
        candidate = OutputCandidate(
            external_selector=result["output"],
            value=result["probability"],
            value_kind="probability",
            meaning="Synthetic positive-class probability",
            positive_direction="increasing",
            event_id=result["event"],
        )
        return NormalizedEnvelope((candidate,))

    def validate_declarations(self, envelope: NormalizedEnvelope,
                              declarations: SourceDeclarations) -> NormalizedEnvelope:
        # This simple demo source has no additional owner-side declarations.
        return envelope


class DemoTrustedLedger:
    """Independent in-memory ledger for the exact synthetic output event."""

    integration_id = "safira-manual-demo-ledger"

    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, str, tuple[str, str, str], tuple[str, str, str]]] = {}
        self._used: set[str] = set()

    def record_export(self, event_id: str, raw_json: str,
                      contribution: ComponentContribution,
                      association: CollectionAssociation) -> None:
        """Record export facts separately before the collector admits the output."""
        self._entries[event_id] = (
            sha256(raw_json.encode("utf-8")).hexdigest(),
            contribution.external_selector,
            contribution.source_key,
            (association.patient_ref, association.assessment_ref, association.occurrence_ref),
        )

    def check_output_link(self, raw_json: str | bytes, candidate: OutputCandidate,
                          contributor: RegisteredModelVersion, label: object,
                          association: CollectionAssociation) -> ProvenanceCheck:
        raw_bytes = raw_json.encode("utf-8") if isinstance(raw_json, str) else raw_json
        event_id = candidate.event_id or ""
        key = (contributor.model_id, contributor.model_version, candidate.external_selector)
        # The contributor's exact registered label is passed separately and
        # replaces the selector in the registered source key.
        label_id = getattr(label, "label_id", "")
        source_key = (contributor.model_id, contributor.model_version, label_id)
        association_key = (association.patient_ref, association.assessment_ref,
                           association.occurrence_ref)
        expected = self._entries.get(event_id)
        matched = expected == (
            sha256(raw_bytes).hexdigest(), candidate.external_selector,
            source_key, association_key,
        )
        unused = event_id not in self._used
        if matched and unused:
            self._used.add(event_id)
        return ProvenanceCheck(
            integration_id=self.integration_id,
            check_method="synthetic independent export-ledger comparison",
            independent_evidence_ref=f"demo-ledger-entry:{event_id}",
            event_id=event_id,
            content_binding_method="SHA-256 of exact JSON bytes compared with prior ledger entry",
            content_bound=matched,
            covered_selector=candidate.external_selector,
            contributor=source_key,
            association=association_key,
            association_bound=matched,
            fresh=True,
            not_revoked=True,
            unused=unused,
        )


def _metadata(classifier: DemoClassifier, adapter: DemoAdapter) -> RegisteredModelVersion:
    return RegisteredModelVersion.from_dict({
        "model_id": "synthetic-demo-classifier",
        "model_version": "1.0.0",
        "metadata_schema_version": 1,
        "task_type": "supervised_single_label_binary_classification",
        "classifier_artifact": {"sha256": sha256(classifier.artifact).hexdigest()},
        "labels": [{
            "label_id": "synthetic-label",
            "negative_outcome": "negative",
            "positive_outcome": "positive",
            "output_selector": 0,
            "value_kind": "probability",
            "value_source": "predict_probability",
            "value_scale": {
                "minimum": 0.0,
                "maximum": 1.0,
                "meaning": "Synthetic positive-class probability",
                "positive_direction": "increasing",
            },
            # This is the registered primary-model class mapping, not a Safira
            # reliability or TRUST/CAUTION/DEFER operating point.
            "class_mapping": {"positive_when": ">=", "boundary": 0.6},
        }],
        "adapter": {
            "adapter_id": "synthetic-demo-adapter",
            "adapter_version": "1.0.0",
            "implementation_fingerprint": sha256(adapter.implementation_artifact).hexdigest(),
            "associated_model_id": "synthetic-demo-classifier",
            "associated_model_version": "1.0.0",
            "capabilities": adapter.capabilities.to_dict(),
        },
        "input": {
            "schema": {"synthetic_feature": {"type": "float", "shape": [1]}},
            "modalities": ["MRI", "clinical"],
        },
        "preprocessing_identity": "synthetic-demo-preprocessing-v1",
    })


def _show_record(title: str, record) -> None:
    print(f"\n{title}")
    print(f"  Model: {record.model_id}  Version: {record.model_version}")
    print(f"  Label: {record.label_id}")
    print(f"  Primary model probability: {record.primary.value:.2f}")
    print(f"  Primary model class: {record.primary.predicted_class}")
    print(f"  Provenance mode: {record.provenance.mode}")
    print(f"  Provenance assurance: {record.provenance.assurance}")
    print("  Provenance details:")
    for name, value in record.provenance.details.items():
        print(f"    {name}: {value}")
    print("  Optional evidence states:")
    for item in record.evidence:
        suffix = f" ({item.reason_code})" if item.reason_code else ""
        print(f"    {item.category}: {item.state}{suffix}")


def main() -> int:
    synthetic_input = {"synthetic_feature": [0.25]}
    association = CollectionAssociation(
        "opaque-demo-patient", "demo-assessment", "demo-occurrence-1"
    )
    interpretation = {
        "feature_representation": {"meaning": "synthetic two-value representation", "shape": [2]},
        "repeated_outputs": {
            "meaning": "independent synthetic model runs",
            "repeat_ids": ["run-1", "run-2"],
            "provenance": "demo run ledger",
        },
        "modality_outputs": {
            "meaning": "synthetic per-modality primary probabilities",
            "modality_ids": ["MRI", "clinical"],
            "output_space": "probability",
        },
        "domain_metadata": {"meaning": "synthetic cohort scope metadata"},
        "explanation": {
            "meaning": "synthetic feature attribution",
            "target_label": "synthetic-label",
            "target_output": "uncalibrated model score",
            "method": "synthetic attribution example",
            "output_space": "uncalibrated_score",
            "calibrated": False,
            "truncated": False,
        },
        "input_metadata": {"meaning": "synthetic input completeness"},
        "available_modalities": {"meaning": "synthetic observed modality identifiers"},
    }

    print("SAFIRA FEATURE 002 - SYNTHETIC COLLECTION DEMO")
    print("No real patient data is used. Values below are illustrative only.")
    print("\nSynthetic input:")
    print(json.dumps(synthetic_input, indent=2))

    with tempfile.TemporaryDirectory(prefix="safira-collection-demo-") as temp_dir:
        db_path = Path(temp_dir) / "registry.sqlite3"
        with ModelRegistry(db_path) as registry:
            classifier = DemoClassifier(b"synthetic classifier artifact v1")
            adapter = DemoAdapter(classifier)
            definition = _metadata(classifier, adapter)
            identity_provider = DemoIdentityProvider(classifier, adapter)
            registry.register(definition, classifier, adapter, identity_provider)
            print("\nPASS: Feature 001 registered the exact synthetic classifier and adapter pair.")
            print(f"  Registered identity: {definition.model_id}@{definition.model_version}")

            live = collect_live(
                registry,
                association,
                [LiveRequest(
                    definition.model_id, definition.model_version, "synthetic-label",
                    available_modalities=("MRI", "clinical"),
                    evidence_interpretation=interpretation,
                )],
                synthetic_input,
            )
            live_record = live.records[0]
            _show_record("LIVE COLLECTION", live_record)
            print("  Live provenance means this process resolved the exact registered,")
            print("  identity-checked classifier-adapter binding before collection.")

            contract = DemoSourceContract()
            ledger = DemoTrustedLedger()
            integration = TrustedSourceIntegration(contract, ledger)
            collector = PrecomputedCollector(registry, [integration])
            event_id = "demo-export-event-1"
            external_selector = "result.probability"
            contribution = ComponentContribution(
                contract.contract_id,
                contract.version,
                external_selector,
                definition.model_id,
                definition.model_version,
                "synthetic-label",
                0,
            )
            source_json = json.dumps({
                "schema": contract.version,
                "result": {
                    "output": external_selector,
                    "probability": live_record.primary.value,
                    "event": event_id,
                },
            }, sort_keys=True)
            # This ledger entry is created independently before ingestion. Its
            # check binds exact bytes, selector/contributor, occurrence, and reuse.
            ledger.record_export(event_id, source_json, contribution, association)
            declarations = SourceDeclarations((contribution,), association=association)
            precomputed = collector.ingest(
                association,
                (contract.contract_id, contract.version),
                source_json,
                declarations,
            )
            precomputed_record = precomputed.records[0]
            _show_record("PRECOMPUTED INGESTION", precomputed_record)
            print("  Precomputed provenance means the trusted synthetic integration checked")
            print("  submitted output against its separate ledger. It does not verify a live")
            print("  Python classifier object or claim that Safira ran that classifier.")

            print("\nCONTROLLED REJECTION")
            rejected_event = "demo-export-event-rejection"
            valid_rejection_source = json.dumps({
                "schema": contract.version,
                "result": {
                    "output": external_selector,
                    "probability": 0.82,
                    "event": rejected_event,
                },
            }, sort_keys=True)
            rejection_candidate = contract.parse(valid_rejection_source).outputs[0]
            ledger.record_export(rejected_event, valid_rejection_source, contribution, association)
            altered_source = valid_rejection_source.replace('"probability": 0.82', '"probability": 0.81')
            try:
                collector.ingest(
                    association,
                    (contract.contract_id, contract.version),
                    altered_source,
                    declarations,
                )
            except ProvenanceCheckFailed as error:
                print(f"  PASS: changed output was rejected ({error.code}).")
            else:
                print("  FAIL: changed output was unexpectedly accepted.")
                return 1

            print("\nIMPORTANT")
            print("  0.82 above is the primary model probability, not Safira reliability.")
            print("  This demo does not train or calibrate a safety model, compute safety")
            print("  signals, or produce TRUST, CAUTION, or DEFER statuses.")
            print("\nPASS: live and precomputed collection demo completed using temporary storage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
