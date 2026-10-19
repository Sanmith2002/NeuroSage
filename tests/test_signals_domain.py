from safira.signals.records import SignalMethodConfig, SignalSourceKey
from safira.signals.reference import (
    ReferenceCompatibilityKey,
    ReferenceFitConfig,
    ReferenceObservation,
    apply_domain_reference,
    crossfit_domain,
    fit_domain_reference,
)


def config():
    source = SignalSourceKey("m", "v1", "label")
    parameters = {"category_field": "site_group", "category_mapping_version": "map-v1",
                  "privacy_approval_ref": "approval-ref"}
    key = ReferenceCompatibilityKey(source, "domain_familiarity", "v1", parameters, "domain-schema", "prep",
                                    "dataset", "protocol", "1", "manifest", "cohort")
    return ReferenceFitConfig(key, SignalMethodConfig("domain_familiarity", "v1", parameters), 2, "one-seed")


def rows(groups=("g1", "g2", "g3", "g4")):
    cfg = config()
    return tuple(ReferenceObservation(f"r{i}", cfg.compatibility_key.source_key, group,
                                      "domain-schema", "prep", domain_category=category,
                                      evidence_ref=f"domain-evidence-{i}")
                 for i, (group, category) in enumerate(zip(groups, ("site-alpha", "site-alpha", "site-beta", "site-gamma"))))


def test_domain_vocabulary_is_training_only_and_result_discloses_only_seen_or_unseen():
    cfg = config()
    state = fit_domain_reference(rows(), cfg)
    seen = apply_domain_reference(state, "site-alpha", cfg.compatibility_key, query_evidence_ref="query-seen")
    unseen = apply_domain_reference(state, "site-secret-new", cfg.compatibility_key, query_evidence_ref="query-unseen")
    assert seen.value == "seen"
    assert unseen.value == "unseen"
    assert "query-seen" in seen.evidence_refs
    assert "site-alpha" not in repr(state)
    assert "site-beta" not in repr(state)


def test_crossfit_excludes_all_rows_from_scored_patient_before_domain_membership():
    training = rows()
    outputs = crossfit_domain(training, config())
    row_by_key = {row.row_key: row for row in training}
    for output in outputs:
        own_group_rows = {row.row_key for row in training if row.patient_group_ref == row_by_key[output.row_key].patient_group_ref}
        assert own_group_rows.isdisjoint(output.reference_row_keys)
    assert "site-alpha" not in repr(outputs)


def test_missing_or_invalid_domain_evidence_is_non_value():
    cfg = config()
    missing = ReferenceObservation("missing", cfg.compatibility_key.source_key, "g1", "domain-schema", "prep",
                                   evidence_ref="ev-missing")
    assert fit_domain_reference((missing,), cfg).status == "missing"
    invalid = ReferenceObservation("invalid", cfg.compatibility_key.source_key, "g1", "domain-schema", "prep",
                                   domain_category=" patient-id:123 ", evidence_ref="ev-invalid")
    assert fit_domain_reference((invalid,), cfg).status == "invalid"
