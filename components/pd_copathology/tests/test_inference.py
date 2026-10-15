"""Frozen inference package, tested on a fully synthetic bundle (fitted on the synthetic development data, then packaged)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil

import jsonschema
import numpy as np
import pandas as pd
import pytest
import yaml

from copath.data.load import COMPONENT_DIR
from copath.inference import (AdditivityError, BundleIntegrityError, InputValidationError, SpecError, contracts, load_bundle, predict_batch,
                              predict_record, schema)
from copath.inference import bundle as bundle_mod
from copath.inference.__main__ import OutputPathError, check_output_path, main
from copath.inference.completeness import completeness
from copath.inference.explanations import SignalExplainer, to_raw_contributions, top_features
from copath.inference.synthetic import DEMO_ID, make_synthetic_record
from copath.models import candidates
from copath.phase3 import packaging
from copath.phase3.core import sha256
from copath.training import train, tuning

from .fixtures import build_phase2_fixtures as fx
from .test_phase3 import _make_bundle, _packaged, phase2  # noqa: F401  (phase2 is a fixture)


@pytest.fixture(scope="module")
def bundle(phase2, tmp_path_factory):  # noqa: F811
    return _make_bundle(tmp_path_factory.mktemp("inference_bundle"), phase2)


@pytest.fixture(scope="module")
def frozen(bundle, tmp_path_factory):
    """(paths, expected hash, loaded Bundle) of a packaged synthetic bundle."""
    paths, digest, _ = _packaged(bundle, tmp_path_factory.mktemp("inference_packaged") / "copy")
    return paths, digest, load_bundle(paths, digest)


def _values(features, seed=7):
    rng = np.random.default_rng(seed)
    return {f: float(round(v, 3)) for f, v in zip(features, rng.uniform(0.1, 5.0, len(features)))}


def _record(loaded, n=None, **extra):
    features = loaded.features if n is None else loaded.features[:n]
    return {"participant_id": DEMO_ID, **_values(features), **extra}


# ------------------------------------------------------------- output contract

def test_output_validates_against_the_json_schema_and_has_exactly_three_frozen_signals(frozen):
    paths, digest, loaded = frozen
    result = predict_record(loaded, _record(loaded, cohort="PD"))
    schema.validate_output(result)
    committed = json.loads((contracts.DOCS / contracts.OUTPUT_SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(committed).validate(result)
    assert list(result["signals"]) == ["pd_type", "ad_like", "vascular_risk"]
    assert [result["signals"][s]["model"] for s in result["signals"]] == ["rf", "lr_enet", "rf"]
    assert [result["signals"][s]["target_definition"] for s in result["signals"]] == ["pd_type_v1", "ad_like_v1", "vascular_v1"]
    assert all(0.0 <= s["probability"] <= 1.0 and s["calibration"] == "sigmoid" for s in result["signals"].values())
    assert result["schema_version"] == "1.0" and result["participant_id"] == DEMO_ID and result["model_version"] == "pd-copathology-v1.0"
    assert result["selected_models_sha256"] == digest and result["disclaimer"] == schema.DISCLAIMER


def test_the_committed_input_contract_is_structurally_valid_and_consistent_with_its_feature_table():
    committed = json.loads((contracts.DOCS / contracts.INPUT_SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(committed)  # a valid JSON Schema
    assert contracts.contract_problems() == []  # structure, canonical order, and markdown table agree with the schema
    table = (contracts.DOCS / contracts.INPUT_TABLE).read_text(encoding="utf-8")
    assert committed["x-contract-source"] == schema.CONTRACT_SOURCE and schema.CONTRACT_SOURCE in table
    assert "intentionally not identical to the broader modelling-tier candidate feature configuration" in table
    order = committed["x-feature-order"]
    features = [n for n, p in committed["properties"].items() if "x-modality" in p]
    assert len(order) == len(set(order)) and set(order) == set(features)
    assert (contracts.DOCS / contracts.OUTPUT_SCHEMA).read_text(encoding="utf-8") == json.dumps(schema.output_schema(), indent=1, ensure_ascii=False) + "\n"
    example = make_synthetic_record({n: m["modality"] for n, m in contracts.read_contract().items()}, cohort="HC")
    jsonschema.Draft202012Validator(committed).validate(example)  # the synthetic example is a valid input
    assert example["participant_id"] == DEMO_ID and example == make_synthetic_record({n: m["modality"] for n, m in contracts.read_contract().items()}, cohort="HC")
    assert all("TBD — student to complete" == committed["properties"][n]["description"] for n in features)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(committed).validate({**example, order[0]: "not a number"})
    assert "Input contract v1 validates presence/missingness and numeric type only" in table


def test_the_tier_feature_listing_is_a_candidate_list_and_never_defines_the_frozen_contract():
    tier = contracts.tier_features()
    assert tier and all(set(m["signals"]) <= set(schema.SIGNAL_NAMES) for m in tier.values())
    candidate = schema.input_schema(tier, source="candidate features (tracked tier configuration), not the frozen contract")
    assert candidate["x-contract-source"] != schema.CONTRACT_SOURCE and candidate["x-feature-order"] == list(tier)
    import inspect

    from copath.inference import __main__ as cli

    assert "tier_features" not in inspect.getsource(cli)  # the command line never writes the contract from the tier configuration


def _bundle_union(paths):
    union = []
    for label in ("pd_type_v1", "ad_like_v1", "vascular_v1"):
        for name in json.loads((paths.models / "v1.0" / label / "features.json").read_text(encoding="utf-8")):
            if name not in union:
                union.append(name)
    return union


def test_from_bundle_generation_writes_exactly_the_bundle_union_in_canonical_order(frozen, tmp_path):
    paths, digest, loaded = frozen
    docs = tmp_path / "docs"
    contracts.write_contracts(contracts.bundle_features(loaded), docs)
    generated = json.loads((docs / contracts.INPUT_SCHEMA).read_text(encoding="utf-8"))
    union = _bundle_union(paths)  # read independently from the synthetic features.json files
    assert generated["x-feature-order"] == union == loaded.features
    assert [n for n in generated["properties"] if n not in ("participant_id", "cohort")] == union
    for name in union:
        meta = generated["properties"][name]
        assert meta["x-signals"] == [s for s in schema.SIGNAL_NAMES if name in loaded.signals[s].features]
        assert meta["x-modality"] == loaded.modality.get(name, "unclassified") and meta["type"] == ["number", "null"]
    assert generated == schema.input_schema(contracts.bundle_features(loaded))
    rows, _ = contracts._read_table(docs / contracts.INPUT_TABLE)
    assert [r[1] for r in rows] == union and [r[0] for r in rows] == list(range(1, len(union) + 1))
    assert contracts.contract_problems(docs=docs) == [] and contracts.check_contracts(loaded, docs) == []


def test_tier_features_that_are_absent_from_the_frozen_bundle_are_excluded_from_the_contract(frozen, tmp_path):
    paths, digest, loaded = frozen
    tier = contracts.tier_features()
    extras = set(tier) - set(loaded.features)
    assert extras  # the tracked tier configuration has candidates the (synthetic) bundle does not use
    docs = tmp_path / "from_bundle"
    contracts.write_contracts(contracts.bundle_features(loaded), docs)
    written = json.loads((docs / contracts.INPUT_SCHEMA).read_text(encoding="utf-8"))
    assert not extras & set(written["properties"]) and not extras & set(written["x-feature-order"])
    assert set(written["x-feature-order"]) == set(loaded.features)
    assert not any(f"`{name}`" in (docs / contracts.INPUT_TABLE).read_text(encoding="utf-8") for name in extras)
    candidate_docs = tmp_path / "from_tier"
    contracts.write_contracts(tier, candidate_docs)  # a contract built from the broader tier configuration ...
    problems = contracts.check_contracts(loaded, candidate_docs)
    assert any("not in the frozen bundle" in p for p in problems)  # ... is caught by the bundle check


def _rewrite(docs, mutate):
    features = contracts.read_contract(docs / contracts.INPUT_SCHEMA)
    features = mutate(features) or features
    contracts.write_contracts(features, docs)  # schema AND markdown stay mutually consistent; only the bundle comparison can catch it


def _swap_first_two(features):
    items = list(features.items())
    items[0], items[1] = items[1], items[0]
    return dict(items)


def _drop(features):
    features.pop(list(features)[3])


def _add(features):
    features["EXTRA_SYNTHETIC_FEATURE"] = {"modality": "motor", "signals": ["pd_type"], "description": schema.TBD}


def _modality(features):
    name = list(features)[2]
    features[name] = {**features[name], "modality": "some other modality"}


def _signals(features):
    name = next(n for n, m in features.items() if len(m["signals"]) > 1)
    features[name] = {**features[name], "signals": features[name]["signals"][:1]}


@pytest.mark.parametrize("mutate, expected", [(_drop, "lacks 1 frozen-bundle feature"), (_add, "not in the frozen bundle"),
                                              (_swap_first_two, "canonical feature order differs"), (_modality, "modality differs"),
                                              (_signals, "signal membership differs")])
def test_check_contracts_fails_on_any_difference_from_the_frozen_bundle(frozen, tmp_path, mutate, expected):
    _, _, loaded = frozen
    docs = tmp_path / "docs"
    contracts.write_contracts(contracts.bundle_features(loaded), docs)
    assert contracts.check_contracts(loaded, docs) == []  # the matching contract passes
    _rewrite(docs, mutate)
    problems = contracts.check_contracts(loaded, docs)
    assert any(expected in p for p in problems), problems


def test_check_contracts_also_fails_when_the_schema_and_the_table_disagree_or_the_source_is_missing(frozen, tmp_path):
    _, _, loaded = frozen
    docs = tmp_path / "docs"
    contracts.write_contracts(contracts.bundle_features(loaded), docs)
    table, schema_file = docs / contracts.INPUT_TABLE, docs / contracts.INPUT_SCHEMA
    original_table, original_schema = table.read_text(encoding="utf-8"), schema_file.read_text(encoding="utf-8")
    table.write_text(original_table.replace("| number |", "| string |", 1), encoding="utf-8")
    assert any("disagrees with the schema" in p for p in contracts.check_contracts(loaded, docs))
    table.write_text(original_table.replace(schema.CONTRACT_SOURCE, "nothing"), encoding="utf-8")
    assert any("contract source" in p for p in contracts.check_contracts(loaded, docs))
    table.write_text(original_table, encoding="utf-8")
    data = json.loads(original_schema)
    del data["x-feature-order"]
    schema_file.write_text(json.dumps(data), encoding="utf-8")
    assert any("x-feature-order" in p for p in contracts.check_contracts(loaded, docs))
    data["x-feature-order"] = list(reversed(loaded.features))  # the JSON key order alone is not the definition of the order
    schema_file.write_text(json.dumps(data), encoding="utf-8")
    problems = contracts.check_contracts(loaded, docs)
    assert any("canonical feature order" in p for p in problems)
    (docs / contracts.INPUT_TABLE).unlink()
    assert contracts.check_contracts(loaded, docs)  # a missing file is a mismatch, not a crash


def test_the_contract_check_is_read_only_and_works_through_the_command_line(frozen, tmp_path, monkeypatch, capsys):
    paths, digest, loaded = frozen
    docs = tmp_path / "docs"
    contracts.write_contracts(contracts.bundle_features(loaded), docs)
    monkeypatch.setattr(bundle_mod, "Paths", lambda: paths)
    monkeypatch.setattr(packaging, "FROZEN_SELECTED_SHA256", digest)
    monkeypatch.setattr(contracts, "DOCS", docs)
    snapshot = lambda: {str(p): sha256(p) for root in (docs, paths.models, paths.frozen) for p in sorted(root.rglob("*")) if p.is_file()}  # noqa: E731
    listing = sorted(p.name for p in tmp_path.rglob("*"))
    before = snapshot()
    assert main(["--check-contracts", "--from-bundle"]) == 0
    assert "matches the frozen bundle" in capsys.readouterr().err and snapshot() == before and sorted(p.name for p in tmp_path.rglob("*")) == listing
    _rewrite(docs, _drop)
    changed = snapshot()
    assert main(["--check-contracts", "--from-bundle"]) == 6
    assert "CONTRACT MISMATCH" in capsys.readouterr().err and snapshot() == changed  # still writes nothing
    for flags in (["--check-contracts"], ["--write-contracts"]):
        with pytest.raises(SystemExit):
            main(flags)  # both need --from-bundle: the contract is never written from the tier configuration
    assert snapshot() == changed
    assert main(["--write-contracts", "--from-bundle"]) == 0 and main(["--check-contracts", "--from-bundle"]) == 0  # regenerated contract matches


def test_explanation_wording_is_exact_and_documented_caveats_are_present(frozen):
    _, _, loaded = frozen
    assert schema.SHAP_EXPLAINS == "uncalibrated model output (not the calibrated probability); contributions do not sum to the probability"
    result = predict_record(loaded, _record(loaded, n=8))
    assert all(s["shap_explains"] == schema.SHAP_EXPLAINS for s in result["signals"].values())
    for folder in (COMPONENT_DIR / "src", COMPONENT_DIR / "docs"):
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".md", ".json"):
                assert "notsum" not in path.read_text(encoding="utf-8"), path.name
    text = (COMPONENT_DIR / "docs" / "output_schema.md").read_text(encoding="utf-8")
    assert "highly correlated, redundant or near-duplicate" in text and "hy / NHY" in text and "independent causal importance" in text
    assert "do not sum to the calibrated probability" in text


def test_no_output_key_or_enumerated_value_is_a_decision_reserved_for_the_safety_framework(frozen):
    _, _, loaded = frozen
    result = predict_record(loaded, _record(loaded, cohort="Prodromal"))
    assert schema._forbidden_names(result) == []
    assert "Not a clinical diagnosis" in result["disclaimer"]  # the disclaimer legitimately uses the word
    assert schema._forbidden_names({"signals": {"trust_level": 1}}) and schema._forbidden_names({"x": {"direction": "defer"}})
    assert schema._forbidden_names({"modality_completeness": {"blood": 1.0}}) == []  # no false positive inside a word
    keys = set(re.findall(r'"([A-Za-z_]+)":', json.dumps(result)))
    assert not keys & {"threshold", "decision", "label", "prediction", "class"}  # no decision threshold or binary decision is output


def test_the_string_in_training_population_appears_nowhere_in_code_schemas_or_docs():
    needle = "in_training_" + "population"
    for folder in (COMPONENT_DIR / "src", COMPONENT_DIR / "docs"):
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".md", ".json", ".yaml"):
                assert needle not in path.read_text(encoding="utf-8"), path.name


# ------------------------------------------------------------- integrity at load

def test_integrity_is_verified_once_before_any_prediction_with_the_same_function_as_the_packaging_command(bundle, tmp_path, monkeypatch):
    from sklearn.calibration import CalibratedClassifierCV

    from copath.phase3 import __main__ as phase3_cli

    paths, digest, _ = _packaged(bundle, tmp_path / "copy")
    assert bundle_mod.verify_bundle is packaging.verify and phase3_cli.packaging.verify is bundle_mod.verify_bundle
    order, real_verify, real_predict = [], packaging.verify, CalibratedClassifierCV.predict_proba

    def verify(*args, **kwargs):
        order.append("verify")
        return real_verify(*args, **kwargs)

    def predict(self, X):
        order.append("predict")
        return real_predict(self, X)

    monkeypatch.setattr(packaging, "verify", verify)
    monkeypatch.setattr(bundle_mod, "verify_bundle", verify)
    monkeypatch.setattr(CalibratedClassifierCV, "predict_proba", predict)
    loaded = load_bundle(paths, digest)
    predict_batch(loaded, [_record(loaded, n) for n in (None, 10, 5)])
    assert order[0] == "verify" and order.count("verify") == 1 and order.count("predict") == 9  # once per load, not per record


@pytest.mark.parametrize("damage", ["file_hash", "feature_order", "selection", "no_specs", "bad_specs", "inconsistent_specs", "sklearn_in_manifest"])
def test_a_changed_bundle_is_refused_before_any_prediction(bundle, tmp_path, monkeypatch, damage):
    paths, digest, _ = _packaged(bundle, tmp_path / "copy")
    folder, root = packaging.packaging_dir(paths, "v1.0"), paths.models / "v1.0" / "ad_like_v1"
    expected = digest
    if damage == "file_hash":
        (root / "model_card.md").write_bytes((root / "model_card.md").read_bytes() + b"x")
    elif damage == "feature_order":
        features = json.loads((root / "features.json").read_text(encoding="utf-8"))
        (root / "features.json").write_text(json.dumps(list(reversed(features)), indent=1) + "\n", encoding="utf-8")
    elif damage == "selection":
        expected = "0" * 64
    elif damage == "no_specs":
        (folder / "explainer_specs.json").unlink()
    elif damage == "bad_specs":
        (folder / "explainer_specs.json").write_text("not json", encoding="utf-8")
    elif damage == "inconsistent_specs":
        specs = json.loads((folder / "explainer_specs.json").read_text(encoding="utf-8"))
        specs["signals"]["ad_like"]["contribution"] = "something else"
        text = json.dumps(specs, indent=1, sort_keys=True) + "\n"
        (folder / "explainer_specs.json").write_text(text, encoding="utf-8")
        manifest = json.loads((folder / "bundle_manifest.json").read_text(encoding="utf-8"))
        manifest["explainer_specs"]["sha256"] = hashlib.sha256(text.encode()).hexdigest()  # a self-consistent hash still disagrees with the pipeline
        (folder / "bundle_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    elif damage == "sklearn_in_manifest":
        manifest = json.loads((folder / "bundle_manifest.json").read_text(encoding="utf-8"))
        manifest["reference_training_library_versions"]["scikit-learn"] = "0.0.1"
        (folder / "bundle_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(bundle_mod, "SignalExplainer", lambda *a, **k: calls.append("explainer"))
    with pytest.raises(BundleIntegrityError, match="no prediction was made"):
        load_bundle(paths, expected)
    assert calls == []  # no explainer, hence no model, was built from the rejected bundle


def test_an_inconsistent_version_warning_when_loading_an_artifact_is_an_error(bundle, tmp_path, monkeypatch):
    import warnings

    from sklearn.exceptions import InconsistentVersionWarning

    paths, digest, _ = _packaged(bundle, tmp_path / "copy")
    real = packaging.joblib.load

    def load(path, *args, **kwargs):
        warnings.warn(InconsistentVersionWarning(estimator_name="Pipeline", current_sklearn_version="9.9", original_sklearn_version="0.0.1"))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(packaging.joblib, "load", load)
    with pytest.raises(BundleIntegrityError, match="another scikit-learn version"):
        load_bundle(paths, digest)


def test_other_library_differences_are_reported_as_warnings_and_the_version_source_is_known(bundle, tmp_path):
    paths, digest, manifest = _packaged(bundle, tmp_path / "copy")
    folder = packaging.packaging_dir(paths, "v1.0")
    changed = json.loads((folder / "bundle_manifest.json").read_text(encoding="utf-8"))
    changed["reference_training_library_versions"]["numpy"] = "0.1"
    (folder / "bundle_manifest.json").write_text(json.dumps(changed, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    loaded = load_bundle(paths, digest)
    assert any("numpy differs" in w for w in loaded.warnings) and loaded.version_source == "selected_cv_run_metadata"


def test_there_is_no_fallback_explainer_for_a_missing_or_unsupported_specification(frozen):
    _, _, loaded = frozen
    model = loaded.signals["ad_like"]
    good = model.explainer.spec
    for broken in ({}, {**good, "explainer": "shap.KernelExplainer"}, {**good, "reference": "mean of a development sample"},
                   {**good, "output_space": "probability"}, {**good, "n_estimator_inputs": good["n_estimator_inputs"] + 1}):
        with pytest.raises(SpecError):
            SignalExplainer("ad_like", model.label, model.family, broken, model.pipeline, model.features)
    rf = loaded.signals["pd_type"]
    for broken in ({**rf.explainer.spec, "background_data": "dev"}, {**rf.explainer.spec, "feature_perturbation": "interventional"}):
        with pytest.raises(SpecError):
            SignalExplainer("pd_type", rf.label, rf.family, broken, rf.pipeline, rf.features)
    with pytest.raises(SpecError):
        SignalExplainer("ad_like", model.label, "hgb", good, model.pipeline, model.features)
    assert not any("KernelExplainer" in p.read_text(encoding="utf-8") for p in (COMPONENT_DIR / "src" / "copath" / "inference").glob("*.py"))


# ------------------------------------------------------------- explanations

def test_rf_explanation_follows_the_packaged_spec_and_adds_up_in_the_recorded_space(frozen):
    _, _, loaded = frozen
    for name in ("pd_type", "vascular_risk"):
        model = loaded.signals[name]
        tree = model.explainer._tree
        assert model.explainer.spec["feature_perturbation"] == "tree_path_dependent" and model.explainer.spec["background_data"] is None
        assert getattr(tree, "data", None) is None  # no background data
        X = pd.DataFrame([_values(model.features)], columns=model.features)
        out = model.explainer.explain(X)
        total = out["base_value"] + float(out["contributions"].sum())
        direct = float(model.pipeline.predict_proba(X)[0, model.explainer.class_index])
        assert abs(total - direct) < 1e-6 and abs(out["output"] - direct) < 1e-12  # probability of the recorded class
        assert model.explainer.space.startswith("probability") and model.explainer.class_index == 1


def test_ad_like_contributions_are_coef_times_scaled_value_and_add_up_to_the_decision_function(frozen):
    _, _, loaded = frozen
    model = loaded.signals["ad_like"]
    values = _values(model.features[:30])
    X = pd.DataFrame([[values.get(f, np.nan) for f in model.features]], columns=model.features)
    out = model.explainer.explain(X)
    scaled = np.asarray(model.pipeline[:-1].transform(X), dtype=float)
    estimator, keep = model.pipeline.named_steps["model"], model.pipeline.named_steps["drop"].keep_
    expected = np.zeros(len(keep))
    expected[keep] = (scaled * estimator.coef_[0])[0]
    np.testing.assert_allclose(out["contributions"], expected, atol=1e-12)
    assert abs(estimator.intercept_[0] + out["contributions"].sum() - float(estimator.decision_function(scaled)[0])) < 1e-9
    assert out["base_value"] == float(estimator.intercept_[0]) and model.explainer.space.startswith("log-odds")
    # the same numbers as shap.LinearExplainer with the full background (the packaged convention): zero scaled reference
    import shap

    background = np.asarray(model.pipeline[:-1].transform(pd.DataFrame([_values(model.features, s) for s in range(40)], columns=model.features)), dtype=float)
    shifted = background - background.mean(axis=0)  # a background whose mean is exactly the zero vector
    explained = shap.LinearExplainer(estimator, shap.maskers.Independent(shifted, max_samples=len(shifted))).shap_values(scaled)
    np.testing.assert_allclose(explained[0], (scaled * estimator.coef_[0])[0], atol=1e-8)


def test_a_deliberately_corrupted_contribution_fails_the_additivity_guard_and_returns_nothing(frozen, monkeypatch):
    _, _, loaded = frozen
    X = lambda m: pd.DataFrame([_values(m.features)], columns=m.features)  # noqa: E731
    ad, rf = loaded.signals["ad_like"], loaded.signals["pd_type"]
    real = ad.explainer.estimator.decision_function
    monkeypatch.setattr(ad.explainer.estimator, "decision_function", lambda data: real(data) + 0.01, raising=False)
    with pytest.raises(AdditivityError, match="no explanation is returned"):
        ad.explainer.explain(X(ad))
    monkeypatch.undo()
    real_values = rf.explainer._tree.shap_values
    monkeypatch.setattr(rf.explainer._tree, "shap_values", lambda data, **k: np.asarray(real_values(data, **k)) * 1.1)
    with pytest.raises(AdditivityError):
        rf.explainer.explain(X(rf))
    monkeypatch.undo()
    monkeypatch.setattr(ad.explainer.estimator, "decision_function", lambda data: real(data) + 0.01, raising=False)
    with pytest.raises(AdditivityError):  # and the whole record fails: a result that does not add up is never returned
        predict_record(loaded, _record(loaded))


def test_contributions_of_a_raw_feature_with_several_estimator_columns_are_summed_and_dropped_features_get_zero():
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    from copath.models.preprocessing import DropDegenerateColumns

    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(120, 4)), columns=["a", "const", "b", "c"])
    X["const"] = 1.0
    X.loc[::3, "b"] = np.nan
    y = (rng.random(120) > 0.5).astype(int)
    pipeline = Pipeline([("drop", DropDegenerateColumns()), ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                         ("scale", StandardScaler()), ("model", LogisticRegression())]).fit(X, y)
    n_kept = int(pipeline.named_steps["drop"].keep_.sum())
    assert pipeline.named_steps["impute"].indicator_.features_.tolist() == [1]  # "b" (kept index 1) has an indicator column
    values = np.arange(1.0, n_kept + 2).reshape(1, -1)  # kept columns, then the one indicator column
    raw = to_raw_contributions(pipeline, values)[0]
    assert list(raw) == [1.0, 0.0, 2.0 + 4.0, 3.0]  # a, const (dropped), b (value + indicator), c
    with pytest.raises(SpecError):
        to_raw_contributions(pipeline, np.ones((1, n_kept + 3)))


def test_top_features_are_observed_only_ranked_deterministically_with_the_sign_as_direction():
    features = ["f_b", "f_a", "f_c", "f_d", "f_e", "f_f", "f_g", "f_h"]
    contributions = np.array([0.5, 0.5, -0.5, 0.0, 0.3, -0.2, 0.9, 0.1])
    observed = {"f_a", "f_b", "f_c", "f_d", "f_e", "f_f"}  # f_g has the largest contribution but was not observed
    top = top_features(contributions, features, observed, {"f_a": "motor"})
    assert [t["feature"] for t in top] == ["f_a", "f_b", "f_c", "f_e", "f_f"]  # ties by name; f_d (exactly 0) and f_g (missing) left out
    assert [t["direction"] for t in top] == ["increases", "increases", "decreases", "increases", "decreases"]
    assert top[0] == {"feature": "f_a", "modality": "motor", "shap": 0.5, "direction": "increases"} and top[1]["modality"] == "unclassified"
    assert top_features(contributions, features, set(), {}) == []
    assert len(top_features(contributions, features, set(features), {})) == 5


def test_missing_features_may_carry_an_internal_contribution_but_never_appear_in_top_features(frozen):
    _, _, loaded = frozen
    model = loaded.signals["ad_like"]
    record = _record(loaded, n=12)
    result = predict_record(loaded, record)
    observed = set(record) - {"participant_id"}
    for signal in result["signals"].values():
        assert len(signal["top_features"]) <= 5 and {t["feature"] for t in signal["top_features"]} <= observed
        for item in signal["top_features"]:
            assert (item["direction"] == "increases") == (item["shap"] > 0) and item["shap"] != 0
        assert signal["shap_space"] and "uncalibrated" in signal["shap_explains"]
    X = pd.DataFrame([[record.get(f, np.nan) for f in model.features]], columns=model.features)
    contributions = model.explainer.explain(X)["contributions"]
    imputed = [f for f, c in zip(model.features, contributions) if f not in observed and c != 0.0]
    assert imputed  # the imputed (missing) features do carry a non-zero internal contribution ...
    assert not set(imputed) & {t["feature"] for t in result["signals"]["ad_like"]["top_features"]}  # ... but are not reported


# ------------------------------------------------------------- input handling

def test_missing_features_become_nan_and_only_the_frozen_pipeline_handles_them(frozen, monkeypatch):
    from sklearn.calibration import CalibratedClassifierCV

    _, _, loaded = frozen
    frames = []
    real = CalibratedClassifierCV.predict_proba

    def spy(self, X):
        frames.append(X.copy())
        return real(self, X)

    monkeypatch.setattr(CalibratedClassifierCV, "predict_proba", spy)
    record = _record(loaded, n=15)
    result = predict_record(loaded, {**record, "participant_id": None, loaded.features[3]: None, loaded.features[4]: ""})
    assert len(frames) == 3 and all(f.shape[0] == 1 for f in frames)
    for model, frame in zip(loaded.signals.values(), frames):
        assert list(frame.columns) == model.features  # the frozen feature order
        assert frame.isna().sum(axis=1).iloc[0] >= len(model.features) - 15  # everything not supplied is NaN (never imputed outside the pipeline)
        for dropped in (loaded.features[3], loaded.features[4]):
            if dropped in frame.columns:
                assert np.isnan(frame[dropped].iloc[0])  # null and empty count as absent
    assert result["participant_id"] is None


def test_extra_fields_are_ignored_and_counted_without_echoing_their_names(frozen):
    _, _, loaded = frozen
    record = {**_record(loaded, n=10), "SECRET_EXTRA_COLUMN": 5, "another_unknown": "text"}
    result = predict_record(loaded, record)
    assert result["data_quality"]["n_unrecognised_fields"] == 2
    assert "SECRET_EXTRA_COLUMN" not in json.dumps(result) and "another_unknown" not in json.dumps(result)
    base = predict_record(loaded, _record(loaded, n=10), generated_at="2031-01-01T00:00:00Z")
    extra = predict_record(loaded, record, generated_at="2031-01-01T00:00:00Z")
    assert base["signals"] == extra["signals"]  # extra fields do not change anything


@pytest.mark.parametrize("bad", ["abc", "1,5", True, float("inf"), "NaN", "inf", [1], {"x": 1}])
def test_a_supplied_value_that_cannot_be_parsed_fails_naming_the_field_without_echoing_it(frozen, monkeypatch, bad):
    from sklearn.calibration import CalibratedClassifierCV

    _, _, loaded = frozen
    monkeypatch.setattr(CalibratedClassifierCV, "predict_proba", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a prediction was made")))
    name = loaded.features[2]
    with pytest.raises(InputValidationError) as caught:
        predict_record(loaded, {**_record(loaded, n=6), name: bad})
    message = str(caught.value)
    assert caught.value.fields == [name] and name in message and str(bad) not in message.replace(name, "")


def test_numbers_as_text_and_numpy_numbers_are_valid_and_all_bad_fields_are_listed(frozen):
    _, _, loaded = frozen
    a, b, c = loaded.features[:3]
    ok = predict_record(loaded, {a: "1.5", b: np.float64(2.0), c: np.int64(3)}, generated_at="2031-01-01T00:00:00Z")
    same = predict_record(loaded, {a: 1.5, b: 2.0, c: 3}, generated_at="2031-01-01T00:00:00Z")
    assert ok == same
    with pytest.raises(InputValidationError) as caught:
        predict_record(loaded, {a: "x", b: "y", c: 3})
    assert caught.value.fields == sorted([a, b])


def test_cohort_scope_is_per_signal_never_inferred_and_unknown_values_are_rejected(frozen):
    _, _, loaded = frozen
    scope = lambda cohort: {k: v["cohort_in_training_scope"] for k, v in predict_record(loaded, {**_record(loaded, n=5), **({} if cohort is None else {"cohort": cohort})})["signals"].items()}  # noqa: E731
    assert scope("Prodromal") == {"pd_type": False, "ad_like": True, "vascular_risk": True}
    assert scope("SWEDD") == {"pd_type": False, "ad_like": True, "vascular_risk": True}
    assert scope("PD") == scope("hc") == {"pd_type": True, "ad_like": True, "vascular_risk": True}
    assert scope(None) == {"pd_type": None, "ad_like": None, "vascular_risk": None} == scope("")
    with pytest.raises(InputValidationError) as caught:
        predict_record(loaded, {**_record(loaded, n=5), "cohort": "Control group"})
    assert caught.value.fields == ["cohort"] and "Control group" not in str(caught.value)
    assert "cohort" not in loaded.features  # never a model feature


def test_completeness_is_computed_before_imputation_overall_per_modality_and_per_signal(frozen):
    _, _, loaded = frozen
    observed_names = loaded.features[::4]
    result = predict_record(loaded, {f: 1.0 for f in observed_names})
    quality = result["data_quality"]
    expected = loaded.features
    assert quality["n_features_expected"] == len(expected) and quality["n_features_observed"] == len(observed_names)
    assert quality["feature_completeness"] == pytest.approx(len(observed_names) / len(expected), abs=1e-6)
    for signal, model in loaded.signals.items():
        assert quality["per_signal_completeness"][signal] == pytest.approx(sum(f in observed_names for f in model.features) / len(model.features), abs=1e-6)
    by = {}
    for f in expected:
        by.setdefault(loaded.modality.get(f, "unclassified"), []).append(f in observed_names)
    for modality, flags in by.items():
        assert quality["modality_completeness"][modality] == pytest.approx(sum(flags) / len(flags), abs=1e-6)
    assert set(quality["available_modalities"]) == {m for m, f in by.items() if any(f)}
    assert set(quality["missing_modalities"]) == {m for m, f in by.items() if not any(f)}
    # a record that supplies a value for an imputed feature changes completeness; the imputation of the others does not
    assert completeness(set(), loaded.signal_features, loaded.modality, 0)["feature_completeness"] == 0.0


def test_an_all_missing_record_gives_valid_json_with_zero_completeness_and_no_top_features(frozen):
    _, _, loaded = frozen
    for record in ({}, {"participant_id": DEMO_ID}, {f: None for f in loaded.features}):
        result = predict_record(loaded, record)
        schema.validate_output(json.loads(json.dumps(result)))
        assert result["data_quality"]["feature_completeness"] == 0.0 and result["data_quality"]["n_features_observed"] == 0
        assert all(v == 0.0 for v in result["data_quality"]["per_signal_completeness"].values())
        assert result["data_quality"]["available_modalities"] == [] and all(s["top_features"] == [] for s in result["signals"].values())
        assert all(0.0 <= s["probability"] <= 1.0 for s in result["signals"].values())


def test_batch_returns_one_result_per_record_in_order_and_names_a_bad_record(frozen):
    _, _, loaded = frozen
    records = [_record(loaded, n=5, participant_id="SYNTHETIC_A"), _record(loaded, n=9, participant_id="SYNTHETIC_B"), {}]
    results = predict_batch(loaded, records)
    assert [r["participant_id"] for r in results] == ["SYNTHETIC_A", "SYNTHETIC_B", None] and len(results) == 3
    with pytest.raises(InputValidationError, match="record 1"):
        predict_batch(loaded, [records[0], {loaded.features[0]: "bad"}])


# ------------------------------------------------------------- safety properties

def test_inference_never_fits_tunes_or_calibrates_and_writes_nothing(bundle, tmp_path, monkeypatch):
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    paths, digest, _ = _packaged(bundle, tmp_path / "copy")
    before = {str(p): sha256(p) for folder in (paths.models, paths.frozen, paths.processed, paths.runs) for p in folder.rglob("*") if p.is_file()}

    def forbidden(name):
        def call(*args, **kwargs):
            raise AssertionError(f"inference called {name}")
        return call

    for owner, names in ((RandomForestClassifier, ("fit",)), (LogisticRegression, ("fit",)), (Pipeline, ("fit", "fit_transform")),
                         (StandardScaler, ("fit", "partial_fit")), (CalibratedClassifierCV, ("fit",)), (tuning, ("tune",)),
                         (train, ("fit_predict", "outer_cv")), (candidates, ("build", "suggest"))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden(f"{owner.__name__}.{name}"))
    loaded = load_bundle(paths, digest)
    predict_batch(loaded, [_record(loaded), _record(loaded, n=7), {}])
    after = {str(p): sha256(p) for folder in (paths.models, paths.frozen, paths.processed, paths.runs) for p in folder.rglob("*") if p.is_file()}
    assert after == before and not paths.reports.exists()  # nothing was written anywhere


def test_the_output_path_is_refused_inside_the_repository_unless_git_ignores_it(tmp_path, monkeypatch):
    assert check_output_path(tmp_path / "result.json") == (tmp_path / "result.json").resolve()  # outside the repository
    tracked_looking = COMPONENT_DIR / "docs" / "SHOULD_NOT_EXIST_result.json"
    with pytest.raises(OutputPathError, match="not git-ignored"):
        check_output_path(tracked_looking)
    ignored = COMPONENT_DIR / "models" / "final" / "result_for_a_test.json"  # models/final/** is git-ignored
    assert check_output_path(ignored) == ignored.resolve()
    monkeypatch.setattr("copath.inference.__main__.load_bundle", lambda *a, **k: (_ for _ in ()).throw(AssertionError("loaded before the path check")))
    source = tmp_path / "in.json"
    source.write_text("{}", encoding="utf-8")
    assert main(["--input", str(source), "--output", str(tracked_looking)]) == 2 and not tracked_looking.exists()


def test_command_line_end_to_end_on_the_synthetic_bundle(bundle, tmp_path, monkeypatch, capsys):
    paths, digest, _ = _packaged(bundle, tmp_path / "copy")
    monkeypatch.setattr(bundle_mod, "Paths", lambda: paths)
    monkeypatch.setattr(packaging, "FROZEN_SELECTED_SHA256", digest)
    example = tmp_path / "synthetic.json"
    assert main(["--make-synthetic-example", str(example), "--missing-modalities", "DAT", "--cohort", "PD"]) == 0
    record = json.loads(example.read_text(encoding="utf-8"))
    matrix = contracts.read_contract()
    assert record["participant_id"] == DEMO_ID and record["cohort"] == "PD"
    assert not any(matrix[k]["modality"] == "DAT" for k in record if k in matrix) and any(matrix[k]["modality"] != "DAT" for k in record if k in matrix)
    monkeypatch.chdir(tmp_path)
    listing = sorted(p.name for p in tmp_path.rglob("*"))
    assert main(["--input", str(example)]) == 0  # printed, nothing written
    out = capsys.readouterr()
    result = json.loads(out.out)
    schema.validate_output(result)
    assert result["participant_id"] == DEMO_ID and "bundle verified" in out.err and sorted(p.name for p in tmp_path.rglob("*")) == listing
    target = tmp_path / "result.json"
    assert main(["--input", str(example), "--output", str(target)]) == 0
    written = json.loads(target.read_text(encoding="utf-8"))
    assert DEMO_ID in target.read_text(encoding="utf-8")
    for name, signal in written["signals"].items():  # a forest's multi-threaded summation can differ in the last digits between calls
        assert signal["probability"] == pytest.approx(result["signals"][name]["probability"], abs=1e-12)
        assert {k: v for k, v in signal.items() if k not in ("probability", "top_features")} == \
            {k: v for k, v in result["signals"][name].items() if k not in ("probability", "top_features")}
        assert [t["feature"] for t in signal["top_features"]] == [t["feature"] for t in result["signals"][name]["top_features"]]
    csv = tmp_path / "records.csv"
    pd.DataFrame([{"participant_id": "SYNTHETIC_1", **{k: str(v) for k, v in list(record.items())[2:8]}},
                  {"participant_id": "SYNTHETIC_2", **{k: "" for k in list(record)[2:8]}}]).to_csv(csv, index=False)
    assert main(["--input", str(csv)]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 2  # several rows: a list, one result each
    used = json.loads((paths.models / "v1.0" / "ad_like_v1" / "features.json").read_text(encoding="utf-8"))[0]
    csv.write_text("participant_id," + used + "\nSYNTHETIC_3,not-a-number\n", encoding="utf-8")
    assert main(["--input", str(csv)]) == 4
    err = capsys.readouterr().err
    assert "INPUT VALIDATION ERROR" in err and "not-a-number" not in err
    (paths.models / "v1.0" / "ad_like_v1" / "model_card.md").write_text("changed", encoding="utf-8")
    assert main(["--input", str(example)]) == 3 and "BUNDLE INTEGRITY ERROR" in capsys.readouterr().err


def test_the_synthetic_example_is_fully_synthetic_and_configurable():
    features = {"f1": "motor", "f2": "motor", "f3": "DAT", "f4": "cognition"}
    full = make_synthetic_record(features)
    assert full["participant_id"] == "SYNTHETIC_DEMO_001" and set(full) == {"participant_id", *features}
    partial = make_synthetic_record(features, ("motor",), "HC")
    assert set(partial) == {"participant_id", "cohort", "f3", "f4"} and partial["f3"] == full["f3"]
    assert all(0 <= v < 10 for k, v in full.items() if k != "participant_id")
    ids = {str(i) for i in fx.UNIVERSE_IDS}
    assert not ids & {str(v) for v in full.values()}  # nothing is taken from the synthetic cohort either
