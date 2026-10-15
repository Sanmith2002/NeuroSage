"""The versioned contract files in ``docs/``: input schema, input feature table, output schema.

PROVENANCE RULE (v1): the committed input contract is the raw pre-pipeline feature union of the FROZEN FINAL BUNDLE
(``python -m copath.inference --write-contracts --from-bundle``). The broader tracked modelling-tier feature sets
(:func:`tier_features`) are candidates only and never define the contract. ``--check-contracts --from-bundle`` compares the
committed files with the bundle and writes nothing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ..data.load import COMPONENT_DIR
from ..features import leakage_guard
from .schema import CONTRACT_SOURCE, METADATA_FIELDS, SIGNAL_NAMES, TBD, input_schema, output_schema

DOCS = COMPONENT_DIR / "docs"
INPUT_SCHEMA, INPUT_TABLE, OUTPUT_SCHEMA = "input_schema_v1.json", "input_features_v1.md", "output_schema_v1.json"
LABELS = {"pd_type": "pd_type_v1", "ad_like": "ad_like_v1", "vascular_risk": "vascular_v1"}
VALIDATION_SCOPE = ("Input contract v1 validates presence/missingness and numeric type only. It does not currently validate clinical "
                    "plausibility, physiological ranges, or feature-specific categorical codes (for example, a binary numeric feature "
                    "supplied as 7). Out-of-range or implausible numeric inputs are still processed by the frozen models and may produce "
                    "unreliable probabilities. Clinical-range validation, categorical-code validation, and out-of-distribution assessment "
                    "are outside the current inference contract and must be handled by the caller, the downstream Clinical Predictive "
                    "Safety Framework, or a future contract version with explicitly documented ranges.")
ROW_RE = re.compile(r"^\| (\d+) \| `([^`]+)` \| (.*?) \| (\w+) \| (.*?) \| (.*) \|$")


def _features(per_signal: dict[str, list[str]], modality: dict[str, str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for signal in SIGNAL_NAMES:
        for name in per_signal[signal]:
            entry = out.setdefault(name, {"modality": modality.get(name, "unclassified"), "signals": [], "description": TBD})
            entry["signals"].append(signal)
    return out


def tier_features() -> dict[str, dict]:
    """Candidate raw features: the union of the tracked primary-tier feature sets. NOT the inference contract (see module doc)."""
    matrix = leakage_guard.load_matrix()
    modality = dict(zip(matrix["feature"], matrix["modality"]))
    per_signal = {s: yaml.safe_load((leakage_guard.FEATURE_SETS_DIR / f"{LABELS[s]}_primary.yaml").read_text(encoding="utf-8"))["features"]
                  for s in SIGNAL_NAMES}
    return _features(per_signal, modality)


def bundle_features(bundle) -> dict[str, dict]:
    """The exact raw features of a verified bundle (features.json per signal), in canonical order: signals in order, first occurrence."""
    return _features(bundle.signal_features, bundle.modality)


def read_contract(path: Path | None = None) -> dict[str, dict]:
    """Feature name -> {modality, signals} from ``input_schema_v1.json`` (in the canonical order ``x-feature-order``)."""
    schema = json.loads((path or DOCS / INPUT_SCHEMA).read_text(encoding="utf-8"))
    props = {name: p for name, p in schema["properties"].items() if "x-modality" in p}
    order = schema.get("x-feature-order") or list(props)
    return {name: {"modality": props[name]["x-modality"], "signals": props[name]["x-signals"]} for name in order if name in props}


def feature_table(features: dict[str, dict]) -> str:
    """The markdown table, in the canonical feature order (the first column is the position)."""
    lines = ["# Input features, version 1.0", "",
             f"**Contract source.** {CONTRACT_SOURCE}", "",
             "Raw, pre-pipeline feature space accepted by the frozen pipelines. The frozen pipelines decide internally which "
             "features reach the estimators (for example a feature that is constant in the training rows is dropped); the caller sends the "
             "raw record, never post-transform values. All features are numeric (`number`); absent or null features are allowed and are "
             "handled only by the frozen pipeline. Unknown fields are ignored and counted (`n_unrecognised_fields`). A supplied value that "
             "is not a number is a validation error naming the field.", "",
             "Optional metadata fields: `participant_id` (echoed, never a feature) and `cohort` (`PD`, `HC`, `Prodromal`, `SWEDD`; used "
             "only for `cohort_in_training_scope`, never a feature).", "",
             f"**Scope of input validation.** {VALIDATION_SCOPE}", "",
             f"Features: {len(features)}. The table is in the canonical feature order (also stored in `x-feature-order` of "
             "`input_schema_v1.json`). Descriptions come only from tracked, non-private documentation; where none exists the entry "
             f"reads \"{TBD}\".", "", "| # | Feature | Modality | Type | Used by | Description |", "|---|---|---|---|---|---|"]
    for position, (name, meta) in enumerate(features.items(), start=1):
        lines.append(f"| {position} | `{name}` | {meta['modality']} | number | {', '.join(meta['signals'])} | {meta.get('description', TBD)} |")
    return "\n".join(lines) + "\n"


def write_contracts(features: dict[str, dict], docs: Path | None = None) -> list[Path]:
    """Write the three contract files for ``features`` (call with the frozen bundle's features)."""
    docs = docs or DOCS
    docs.mkdir(parents=True, exist_ok=True)
    targets = {INPUT_SCHEMA: json.dumps(input_schema(features), indent=1, ensure_ascii=False) + "\n",
               INPUT_TABLE: feature_table(features),
               OUTPUT_SCHEMA: json.dumps(output_schema(), indent=1, ensure_ascii=False) + "\n"}
    for name, text in targets.items():
        (docs / name).write_text(text, encoding="utf-8", newline="\n")
    return [docs / name for name in targets]


# --------------------------------------------------------------------------
# consistency checks (read-only)
# --------------------------------------------------------------------------

def _read_table(path: Path) -> tuple[list[tuple], str]:
    text = path.read_text(encoding="utf-8")
    return [(int(m.group(1)), m.group(2), m.group(3), m.group(4), [s.strip() for s in m.group(5).split(",")])
            for m in (ROW_RE.match(line) for line in text.splitlines()) if m], text


def _names(items, limit: int = 8) -> str:
    items = sorted(items)
    return ", ".join(items[:limit]) + (f" (+{len(items) - limit} more)" if len(items) > limit else "")


def contract_problems(expected: dict[str, dict] | None = None, docs: Path | None = None) -> list[str]:
    """Problems of the committed input contract. Always checks the schema's structure and that the markdown table agrees with the
    schema; with ``expected`` (the frozen bundle's features, in canonical order) it also checks the contract against the bundle.
    Reads only; writes nothing."""
    docs, problems = docs or DOCS, []
    try:
        schema = json.loads((docs / INPUT_SCHEMA).read_text(encoding="utf-8"))
        rows, text = _read_table(docs / INPUT_TABLE)
    except (OSError, ValueError) as exc:
        return [f"a contract file is missing or invalid ({type(exc).__name__})"]
    import jsonschema

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError:
        problems.append("input_schema_v1.json is not a valid JSON Schema")
    props = schema.get("properties", {})
    features = {n: p for n, p in props.items() if n not in METADATA_FIELDS}
    order = schema.get("x-feature-order")
    if schema.get("x-contract-source") != CONTRACT_SOURCE:
        problems.append("input_schema_v1.json does not state the frozen-bundle contract source")
    if CONTRACT_SOURCE not in text:
        problems.append("input_features_v1.md does not state the frozen-bundle contract source")
    if not isinstance(order, list) or len(set(order)) != len(order) or set(order) != set(features):
        problems.append("x-feature-order is missing, has duplicates, or does not list exactly the feature properties")
        order = list(features)
    for name, p in features.items():
        if p.get("type") != ["number", "null"] or not isinstance(p.get("x-modality"), str) or not set(p.get("x-signals", [])) <= set(SIGNAL_NAMES) \
                or not p.get("x-signals"):
            problems.append(f"{name}: malformed feature entry in the schema (type / modality / signals)")
    if [r[1] for r in rows] != order or [r[0] for r in rows] != list(range(1, len(order) + 1)):
        problems.append("the feature table of input_features_v1.md does not list the schema's canonical feature order")
    else:
        for (_, name, modality, dtype, signals) in rows:
            p = features.get(name, {})
            if modality != p.get("x-modality") or signals != p.get("x-signals") or dtype != "number":
                problems.append(f"{name}: the markdown table disagrees with the schema (modality / type / signals)")
    if f"Features: {len(order)}." not in text:
        problems.append("the feature count in input_features_v1.md does not match the schema")
    if expected is not None:
        want = list(expected)
        if set(want) - set(order):
            problems.append(f"the contract lacks {len(set(want) - set(order))} frozen-bundle feature(s): {_names(set(want) - set(order))}")
        if set(order) - set(want):
            problems.append(f"the contract has {len(set(order) - set(want))} feature(s) that are not in the frozen bundle: {_names(set(order) - set(want))}")
        if set(want) == set(order) and want != order:
            problems.append("the canonical feature order differs from the frozen bundle's feature order")
        for name in set(want) & set(features):
            p = features[name]
            if p.get("x-modality") != expected[name]["modality"]:
                problems.append(f"{name}: modality differs from the frozen bundle")
            if p.get("x-signals") != expected[name]["signals"]:
                problems.append(f"{name}: signal membership differs from the frozen bundle")
    return problems


def check_contracts(bundle, docs: Path | None = None) -> list[str]:
    """Compare the committed input contract with the verified frozen bundle (read-only)."""
    return contract_problems(bundle_features(bundle), docs)
