"""In-memory construction of independently supervised grouped examples."""

from hashlib import sha256
import json
from collections.abc import Mapping

from .exceptions import DatasetProtocolError
from .records import *
from .partitioning import assign_groups, deduplicate, resolve_groups, check_prior_history
from .validation import exact_label, validate_binding, correctness, validate_timing, validate_transformations, validate_prediction_provenance
from .verification import (validate_outcome_check, validate_independence_check, validate_linkage_check,
    validate_timing_check, validate_transformation_check, prediction_fingerprint,
    validate_prediction_admission, validate_manifest_receipt)

def _resolve_namespaces(predictions, declaration, source_namespaces):
    result = {}
    for record in predictions:
        fingerprint = prediction_fingerprint(record)
        explicit = source_namespaces.get(fingerprint) if isinstance(source_namespaces, Mapping) else None
        details = record.provenance.details
        embedded = details.get("source_namespace") or details.get("source_contract_id")
        candidates = {namespace for namespace, patient in declaration.entries
                      if patient == record.association.patient_ref}
        namespace = explicit if explicit is not None else embedded
        if namespace is None and len(candidates) == 1:
            namespace = next(iter(candidates))
        if explicit is not None and embedded is not None and explicit != embedded:
            raise DatasetProtocolError("source_namespace_conflict")
        if type(namespace) is not str or not namespace.strip() or namespace == "unknown":
            raise DatasetProtocolError("source_namespace_required")
        if (namespace, record.association.patient_ref) not in declaration.entries:
            raise DatasetProtocolError("source_namespace_conflict")
        result[fingerprint] = namespace
    return result


class DatasetBuilder:
    VERSION="1.0.0"
    def __init__(self, registry, trusted_verifier):
        self.registry=registry; self.verifier=trusted_verifier

    def build(self, predictions, outcomes, target_definitions, target_bindings, linkage_declaration, protocol,
              *, prior_manifests=(), timing_declarations=(), independence_evidence=(),
              transformation_declarations=(), protected_artifact_handoff=None,
              manifest_handoff=None, source_namespaces=None, group_attributes=None):
        if not isinstance(protocol,EvaluationProtocol): raise DatasetProtocolError("protocol_required")
        target_definitions=tuple(target_definitions); target_bindings=tuple(target_bindings)
        targets={(x.target_id,x.target_version):x for x in target_definitions}
        bindings={x.source_key:x for x in target_bindings}
        protocol_target=targets.get((protocol.target_id,protocol.target_version))
        if protocol_target is None or len(targets)!=len(target_definitions) or len(bindings)!=len(target_bindings):
            return self._empty(protocol,"NOT_READY","target_or_binding_definition_invalid")
        outcomes=tuple(outcomes); predictions=deduplicate(tuple(predictions)); prior_manifests=tuple(prior_manifests)
        admitted=[]; exclusions=[]; admission_lineage=[]
        for prediction in predictions:
            try:
                check=self.verifier.verify_prediction_admission(prediction)
                validate_prediction_admission(check,prediction)
                admitted.append(prediction)
                admission_lineage.append((check.authority,check.method,check.evidence_ref,check.record_fingerprint))
            except Exception:
                exclusions.append(ExclusionRecord("controlled-record-ref","prediction_admission_unverified","admission"))
        predictions=tuple(admitted)
        if not predictions:
            return self._empty(protocol,"NOT_READY","prediction_admission_unverified",exclusions)
        try:
            namespaces=_resolve_namespaces(predictions,linkage_declaration,source_namespaces or {})
        except DatasetProtocolError as error:
            reason="source_namespace_required" if str(error)=="source_namespace_required" else "source_namespace_conflict"
            return self._empty(protocol,"NOT_READY",reason,exclusions)
        try:
            candidate_aliases=tuple((namespaces[prediction_fingerprint(r)],r.association.patient_ref) for r in predictions)
            link_check=self.verifier.verify_linkage(linkage_declaration,candidate_aliases,protocol)
            validate_linkage_check(link_check,linkage_declaration,candidate_aliases)
        except Exception:
            raise DatasetProtocolError("linkage_verification_failed") from None
        aliases=resolve_groups(predictions,linkage_declaration,namespaces)
        grouped={aliases[(namespaces[prediction_fingerprint(r)],r.association.patient_ref)] for r in predictions}
        prior_protected,prior_checks=check_prior_history(self.verifier,prior_manifests,protocol.protocol_id+":"+protocol.protocol_version,protocol,include_checks=True)
        if prior_protected is None:
            return self._empty(protocol,"NOT_READY","prior_history_unknown")
        try:
            assignments=assign_groups(grouped,protocol,group_attributes)
        except DatasetProtocolError as error:
            code=str(error)
            if code == "partition_constraints_infeasible":
                return self._empty(protocol,"INSUFFICIENT_EVIDENCE","partition_configuration_infeasible",exclusions)
            reason = code if code in {"unsupported_partition_constraint","partition_metadata_missing","invalid_partition_constraint"} else "partition_configuration_invalid"
            return self._empty(protocol,"NOT_READY",reason,exclusions)
        if any(assignments.get(g)!="protected_test" for g in prior_protected if g in assignments):
            return self._empty(protocol,"NOT_READY","protected_assignment_conflict")
        if protocol.require_transform_declarations and not transformation_declarations:
            return self._empty(protocol,"NOT_READY","transform_declarations_required")
        if protocol.require_transform_declarations:
            declared_sources={t.source_key if hasattr(t,"source_key") else t.get("source_key") for t in transformation_declarations if isinstance(t,Mapping) or hasattr(t,"source_key")}
            if not {r.source_key for r in predictions}.issubset(declared_sources):
                return self._empty(protocol,"NOT_READY","transform_scope_missing")
        held_out={g for g,role in assignments.items() if role in ("validation","calibration","protected_test")}
        verification_lineage=[("prediction_admission",)+entry for entry in admission_lineage]
        verification_lineage.append(("linkage",link_check.authority,link_check.method,link_check.evidence_ref))
        registration_lineage=[]
        independence_by_key={(x.model_id,x.model_version,x.label_id,x.target_id,x.target_version):x for x in independence_evidence}
        outcome_by_key={}
        for o in outcomes:
            outcome_by_key.setdefault((o.patient_ref,o.assessment_ref,o.label_id,o.target_id,o.target_version),[]).append(o)
        rows=[]
        for prediction in predictions:
            try:
                validate_prediction_provenance(prediction)
                validate_timing(prediction,timing_declarations,required_categories=protocol.required_timing_categories)
                for timing in timing_declarations:
                    if timing.source_key==prediction.source_key and timing.occurrence_ref==prediction.association.occurrence_ref:
                        timing_check=self.verifier.verify_timing(timing,prediction,protocol)
                        validate_timing_check(timing_check,timing)
                        verification_lineage.append(("timing",timing_check.authority,timing_check.method,timing_check.evidence_ref))
                target_key=(protocol.target_id,protocol.target_version)
                target=targets[target_key]; binding=bindings[prediction.source_key]
                metadata,label=exact_label(self.registry,prediction); validate_binding(target,binding,prediction,label)
                registration_lineage.append((prediction.model_id,prediction.model_version,prediction.label_id,label.positive_outcome,label.negative_outcome,metadata.classifier_artifact["sha256"],metadata.preprocessing_identity))
                if transformation_declarations:
                    matching=[]
                    for transformation in transformation_declarations:
                        source_key=transformation.get("source_key") if isinstance(transformation,Mapping) else getattr(transformation,"source_key",None)
                        if source_key==prediction.source_key:
                            transform_check=self.verifier.verify_transformation(transformation,protocol)
                            validate_transformation_check(transform_check,transformation)
                            matching.append(transformation)
                            verification_lineage.append(("transformation",transform_check.authority,transform_check.method,transform_check.evidence_ref))
                    if protocol.require_transform_declarations and not matching:
                        raise DatasetProtocolError("transform_scope_missing")
                    validate_transformations(matching,held_out,source_key=prediction.source_key,registered_identity=metadata.preprocessing_identity)
                candidates=outcome_by_key.get((prediction.association.patient_ref,prediction.association.assessment_ref,prediction.label_id,target.target_id,target.target_version),[])
                if len(candidates)!=1: raise ValueError
                outcome=candidates[0]
                check=self.verifier.verify_outcome(outcome,prediction,target,binding); validate_outcome_check(check,outcome,binding)
                evidence=independence_by_key[(prediction.model_id,prediction.model_version,prediction.label_id,target.target_id,target.target_version)]
                independent=self.verifier.verify_independence(prediction,metadata,evidence,protocol); validate_independence_check(independent,prediction,evidence,protocol)
                verification_lineage.append(("outcome",check.authority,check.method,check.evidence_ref))
                verification_lineage.append(("independence",independent.authority,independent.method,independent.evidence_ref))
                coding=target.outcome_coding
                if outcome.outcome_value not in coding: raise ValueError
                binary=coding[outcome.outcome_value]
                group=aliases[(namespaces[prediction_fingerprint(prediction)],prediction.association.patient_ref)]
                rows.append(CorrectnessExample(prediction,target.target_id,target.target_version,binary,correctness(prediction,binary,target,binding),group,assignments[group],check.evidence_ref,independent.evidence_ref))
            except Exception:
                exclusions.append(ExclusionRecord("controlled-record-ref","evidence_or_compatibility_failed","eligibility"))
        train=tuple(r for r in rows if r.partition_role=="train"); validation=tuple(r for r in rows if r.partition_role=="validation"); calibration=tuple(r for r in rows if r.partition_role=="calibration"); protected=tuple(r for r in rows if r.partition_role=="protected_test")
        state="ready"; reasons=()
        development_rows=train+validation+calibration
        criteria=dict(protocol.adequacy_criteria)
        if protocol.require_adequacy_criteria and not criteria:
            return self._empty(protocol,"NOT_READY","adequacy_criteria_required",exclusions)
        counts={"examples":len(development_rows),"patient_groups":len({r.patient_group_ref for r in development_rows}),
                "positive_outcomes":sum(r.outcome==1 for r in development_rows),"negative_outcomes":sum(r.outcome==0 for r in development_rows),
                "incorrect_predictions":sum(r.correctness_target==0 for r in development_rows),"correct_predictions":sum(r.correctness_target==1 for r in development_rows)}
        failed_criteria=[]
        if not development_rows: failed_criteria.append("no_eligible_development_examples")
        criterion_keys={"minimum_examples":"examples","minimum_patient_groups":"patient_groups",
            "minimum_positive_outcomes":"positive_outcomes","minimum_negative_outcomes":"negative_outcomes",
            "minimum_incorrect_predictions":"incorrect_predictions","minimum_correct_predictions":"correct_predictions"}
        for criterion,key in criterion_keys.items():
            if criterion in criteria and counts[key] < criteria[criterion]: failed_criteria.append(criterion+"_not_met")
        labels={r.prediction.label_id for r in development_rows}
        for label_id in criteria.get("required_labels",()):
            if label_id not in labels: failed_criteria.append("required_label_missing")
        source_scopes=set(r.prediction.source_key for r in development_rows) | set(protocol.adequacy_by_source)
        criterion_keys_by_scope = {
            "minimum_examples_per_label": "examples",
            "minimum_positive_outcomes_per_label": "positive_outcomes",
            "minimum_negative_outcomes_per_label": "negative_outcomes",
            "minimum_correct_predictions_per_label": "correct_predictions",
            "minimum_incorrect_predictions_per_label": "incorrect_predictions",
            "minimum_groups_per_label": "patient_groups",
        }
        for source_scope in source_scopes:
            label_rows=[r for r in development_rows if r.prediction.source_key==source_scope]
            scope_counts={
                "minimum_examples": len(label_rows),
                "minimum_patient_groups": len({r.patient_group_ref for r in label_rows}),
                "minimum_positive_outcomes": sum(r.outcome==1 for r in label_rows),
                "minimum_negative_outcomes": sum(r.outcome==0 for r in label_rows),
                "minimum_correct_predictions": sum(r.correctness_target==1 for r in label_rows),
                "minimum_incorrect_predictions": sum(r.correctness_target==0 for r in label_rows),
            }
            per_label={"minimum_examples_per_label":len(label_rows),
                "minimum_positive_outcomes_per_label":sum(r.outcome==1 for r in label_rows),
                "minimum_negative_outcomes_per_label":sum(r.outcome==0 for r in label_rows),
                "minimum_correct_predictions_per_label":sum(r.correctness_target==1 for r in label_rows),
                "minimum_incorrect_predictions_per_label":sum(r.correctness_target==0 for r in label_rows),
                "minimum_groups_per_label":len({r.patient_group_ref for r in label_rows})}
            scoped_criteria=dict(protocol.adequacy_by_source.get(source_scope,{}))
            for scoped_key, minimum in scoped_criteria.items():
                if scoped_key in scope_counts and scope_counts[scoped_key] < minimum:
                    failed_criteria.append("adequacy_scope_not_met")
                elif scoped_key == "maximum_outcome_imbalance_ratio":
                    positive=scope_counts["minimum_positive_outcomes"]
                    negative=scope_counts["minimum_negative_outcomes"]
                    observed=float("inf") if min(positive,negative)==0 else max(positive,negative)/min(positive,negative)
                    if observed>minimum: failed_criteria.append("adequacy_scope_not_met")
            for criterion,count in per_label.items():
                if criterion in criteria and count<criteria[criterion]: failed_criteria.append(criterion+"_not_met")
                scoped_key=criterion_keys_by_scope[criterion]
                if scoped_key in scoped_criteria and count<scoped_criteria[scoped_key]:
                    failed_criteria.append("adequacy_scope_not_met")
        required_modalities=set(criteria.get("required_modalities",()))
        if required_modalities:
            for row in development_rows:
                evidence=next((item for item in row.prediction.evidence if item.category=="available_modalities" and item.state=="available"),None)
                available=set(evidence.value) if evidence is not None and isinstance(evidence.value,(tuple,list)) else set()
                if not required_modalities.issubset(available):
                    failed_criteria.append("required_modality_missing"); break
        ratio=criteria.get("maximum_outcome_imbalance_ratio")
        if ratio is not None:
            positive=counts["positive_outcomes"]; negative=counts["negative_outcomes"]
            observed=float("inf") if min(positive,negative)==0 else max(positive,negative)/min(positive,negative)
            if observed>ratio: failed_criteria.append("outcome_imbalance_not_met")
        if failed_criteria: state="INSUFFICIENT_EVIDENCE"; reasons=tuple(failed_criteria)
        canonical={"protocol":(protocol.protocol_id,protocol.protocol_version),"target":(protocol.target_id,protocol.target_version),"assignments":assignments,"rows":sorted((r.prediction.source_key,r.prediction.association.assessment_ref,r.prediction.association.occurrence_ref,r.outcome,r.correctness_target,r.verification_ref,r.independence_ref) for r in rows),"outcome_content_refs":sorted(o.content_ref for o in outcomes)}
        dataset_id=sha256(json.dumps(canonical,sort_keys=True,default=list).encode()).hexdigest()
        ref="manifest:"+dataset_id
        manifest_sources=tuple(sorted({"|".join(r.source_key)+"|"+r.provenance.mode for r in predictions}))
        manifest_metadata={"seed":protocol.seed,"algorithm_version":protocol.algorithm_version,"partition_mode":protocol.partition_mode,"allocation_order":protocol.allocation_order,"hard_constraints":protocol.hard_constraints,"adequacy_criteria":protocol.adequacy_criteria,"adequacy_by_source":tuple((tuple(scope),dict(value)) for scope,value in protocol.adequacy_by_source.items()),"linkage_id":linkage_declaration.linkage_id,"linkage_version":linkage_declaration.linkage_version,"linkage_source":linkage_declaration.source_id,"linkage_evidence_ref":linkage_declaration.evidence_ref,"target_id":protocol.target_id,"target_version":protocol.target_version,"target_meanings":(protocol_target.positive_meaning,protocol_target.negative_meaning),"target_coding":protocol_target.outcome_coding,"registration_lineage":tuple(sorted(set(registration_lineage))),"outcome_content_refs":tuple(sorted(o.content_ref for o in outcomes)),"outcome_verification_refs":tuple(sorted(r.verification_ref for r in rows)),"independence_verification_refs":tuple(sorted(r.independence_ref for r in rows)),"verification_lineage":tuple(sorted(verification_lineage)),"prior_manifest_versions":tuple(sorted(m.manifest_id+":"+m.content_version for m in prior_manifests)),"prior_history_verification_refs":tuple(sorted(c.evidence_ref for c in prior_checks)),"prior_history_coverage_versions":tuple(sorted(c.content_version+":"+c.state for c in prior_checks)),"transform_refs":tuple(sorted(str(getattr(t,"transform_id",t.get("transform_id","unknown") if isinstance(t,Mapping) else "unknown"))+":"+str(getattr(t,"transform_version",t.get("transform_version","unknown") if isinstance(t,Mapping) else "unknown")) for t in transformation_declarations))}
        manifest=DatasetManifest(dataset_id,protocol.protocol_id,protocol.protocol_version,self.VERSION,assignments,manifest_sources,tuple(exclusions),manifest_metadata)
        ref="manifest:"+manifest.digest
        manifest_receipt=None
        if manifest_handoff is not None:
            try:
                manifest_receipt=manifest_handoff.accept(manifest,protocol,ref)
                validate_manifest_receipt(manifest_receipt,manifest,ref)
            except Exception:
                return self._empty(protocol,"NOT_READY","manifest_handoff_failed",exclusions)
        if protocol.require_protected_handoff and protected:
            if protected_artifact_handoff is None: return self._empty(protocol,"NOT_READY","protected_handoff_required",exclusions)
            try:
                receipt=protected_artifact_handoff.accept(ProtectedTestArtifact(protected),protocol,ref)
                if type(receipt) is not ProtectedArtifactReceipt or receipt.status!="accepted": raise ValueError
                receipt=ProtectedArtifactReceipt("accepted")
            except Exception:
                return self._empty(protocol,"NOT_READY","protected_handoff_failed",exclusions)
        else: receipt=None
        summary={}
        if "row_count" in protocol.permitted_summaries: summary["example_count"]=len(development_rows)
        if "group_count" in protocol.permitted_summaries: summary["patient_group_count"]=len({r.patient_group_ref for r in development_rows})
        result=DatasetBuildResult(PartitionedDataset(train,validation,calibration),DatasetReadiness(state,reasons,protocol.protocol_id+":"+protocol.protocol_version),tuple(exclusions),ref,receipt,summary,manifest_receipt)
        return result

    def _empty(self,protocol,state,reason,exclusions=()):
        summary={"example_count":0} if "row_count" in protocol.permitted_summaries else {}
        return DatasetBuildResult(PartitionedDataset(),DatasetReadiness(state,(reason,),protocol.protocol_id+":"+protocol.protocol_version),tuple(exclusions),"manifest:unpublished",None,summary)
