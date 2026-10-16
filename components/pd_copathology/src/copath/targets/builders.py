"""Build PD-type, AD-like and vascular-risk targets from targets/*.yaml.

Every label is 1 (positive), 0 (negative) or NaN (masked / not eligible).
Masked is never turned into negative. Numbers that define a label (cut-offs,
technical limits, component counts) are read from the target cards; nothing
is hard-coded here, and a card that lacks a required value stops the build.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PRIMARY_LABELS = ["pd_type_v1", "ad_like_v1", "vascular_v1"]
CARD_FILES = ["pd_type_v1", "pd_type_saa_v1", "ad_like_v1", "ad_like_lumipulse_v1", "vascular_v1", "vascular_v2"]
LABEL_PREFIX = "label_"


class CardError(ValueError):
    """A target card is missing something the builder needs."""


def label_column(label_id: str) -> str:
    return LABEL_PREFIX + label_id


def load_cards(targets_dir: Path) -> dict[str, dict]:
    """Load and validate every target card, keyed by ``<target_id>_<version>``."""
    cards = {}
    for name in CARD_FILES:
        path = Path(targets_dir) / f"{name}.yaml"
        if not path.is_file():
            raise CardError(f"target card missing: {name}.yaml")
        card = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        validate_card(card, name)
        cards[name] = card
    return cards


def validate_card(card: dict, name: str) -> None:
    """Every card must state the same set of things, whatever its layout details."""
    rule = card.get("rule") or {}
    required = {
        "target ID": card.get("target_id"), "version": card.get("version"), "status": card.get("status"),
        "construct": card.get("construct"), "source": card.get("source"),
        "eligible population": card.get("eligible_population"),
        "positive rule": rule.get("positive"), "negative rule": rule.get("negative"), "masked rule": rule.get("masked"),
        "technical-value handling": card.get("preprocessing"), "leakage-defining features": card.get("leakage"),
        "citation": rule.get("citation") or rule.get("cutoff_source"),
    }
    missing = [what for what, value in required.items() if value in (None, "", {}, [])]
    if "sensitivity_variants" not in card:
        missing.append("sensitivity variants")
    if missing:
        raise CardError(f"{name}.yaml lacks: {', '.join(missing)}")
    if card_label(card) != name:
        raise CardError(f"{name}.yaml: target_id and (major) version do not match the file name")
    if str(rule["masked"]).strip() == str(rule["negative"]).strip():
        raise CardError(f"{name}.yaml: the masked rule must be distinct from the negative rule")


def card_label(card: dict) -> str:
    """Label id of a card: target id plus the major version (card v1.1 still defines label ``_v1``)."""
    return f"{card['target_id']}_{str(card['version']).split('.')[0]}"


def variant_parents(cards: dict[str, dict]) -> dict[str, str]:
    """Label id -> the card whose leakage column it uses (itself for a card, the parent for a variant)."""
    parents = {name: name for name in cards}
    for name, card in cards.items():
        for variant in card.get("sensitivity_variants") or []:
            parents.setdefault(str(variant["id"]), name)
    return parents


def _tri(positive: pd.Series, eligible: pd.Series) -> pd.Series:
    """1 / 0 / NaN from a positive mask and an eligibility mask."""
    return pd.Series(np.where(eligible, np.where(positive, 1.0, 0.0), np.nan), index=positive.index)


# --------------------------------------------------------------------------
# PD-type
# --------------------------------------------------------------------------

def pd_type(cohort: pd.Series, card: dict) -> pd.Series:
    rule = card["rule"]
    positive, negative = cohort.isin(rule["positive_cohorts"]), cohort.isin(rule["negative_cohorts"])
    return _tri(positive, positive | negative)


def saa_status_at_baseline(saa: pd.DataFrame, event_column: str, status_column: str, baseline_event: str,
                           key: str = "PATNO") -> pd.DataFrame:
    """One row per participant with a BL result: the common status, or ``Conflicting``."""
    rows = saa[(saa[event_column] == baseline_event) & (saa[status_column].astype(str).str.strip() != "")]
    grouped = rows.groupby(key)[status_column]
    distinct, first = grouped.nunique(), grouped.first()
    status = first.where(distinct == 1, "Conflicting")
    return pd.DataFrame({key: status.index, "saa_status_bl": status.to_numpy(),
                         "saa_n_results_bl": grouped.size().to_numpy()})


def pd_type_saa(status: pd.Series, card: dict) -> pd.Series:
    rule = card["rule"]
    positive, negative = status == rule["positive_status"], status == rule["negative_status"]
    return _tri(positive, positive | negative)


# --------------------------------------------------------------------------
# AD-like (Elecsys)
# --------------------------------------------------------------------------

_NUMBER = r"([0-9]+(?:\.[0-9]+)?)"
_FLAG_BRANCH = re.compile(r"elif\s+(\w+)\s*==\s*1\s*:\s*" + _NUMBER)


def ad_like_parameters(card: dict) -> dict:
    """Read the AD-like formula, limits, limit flags and cut-off from the card. Stops if anything is absent.

    The curated cut discards out-of-range Elecsys values and keeps only limit
    flags, so the card (v1.1) says which boundary value replaces each flagged
    measurement. Those are boundary substitutions for censored measurements,
    not the participants' true values.
    """
    pre, rule = card.get("preprocessing") or {}, card.get("rule") or {}
    absent = [k for k in ("derived_value", "abeta_used", "ptau_used") if not pre.get(k)]
    if rule.get("cutoff") in (None, ""):
        absent.append("cutoff")
    if absent:
        raise CardError(f"ad_like_v1.yaml does not define: {', '.join(absent)}. The label is not built; nothing is guessed.")
    abeta_rule, ptau_rule = " ".join(str(pre["abeta_used"]).split()), " ".join(str(pre["ptau_used"]).split())
    clamp = re.search(r"min\(\s*max\(\s*abeta\s*,\s*" + _NUMBER + r"\s*\)\s*,\s*" + _NUMBER + r"\s*\)", abeta_rule)
    floor = re.search(r"max\(\s*ptau\s*,\s*" + _NUMBER + r"\s*\)", ptau_rule)
    if not clamp or not floor:
        raise CardError("ad_like_v1.yaml: abeta_used / ptau_used are not of the form "
                        "min(max(abeta, X), Y) / max(ptau, Z) followed by the limit-flag branches")
    abeta_floor, abeta_cap, ptau_floor = float(clamp.group(1)), float(clamp.group(2)), float(floor.group(1))
    abeta_flags = {name: float(value) for name, value in _FLAG_BRANCH.findall(abeta_rule)}
    ptau_flags = {name: float(value) for name, value in _FLAG_BRANCH.findall(ptau_rule)}
    if sorted(abeta_flags.values()) != [abeta_floor, abeta_cap] or list(ptau_flags.values()) != [ptau_floor]:
        raise CardError("ad_like_v1.yaml: the limit-flag branches of abeta_used / ptau_used do not agree with the limits")
    if re.sub(r"\s+", "", str(pre["derived_value"])) != "ratio=ptau_used/abeta_used":
        raise CardError("ad_like_v1.yaml: derived_value is not 'ratio = ptau_used / abeta_used'")
    for key, value in (("abeta_cap", abeta_cap), ("abeta_floor", abeta_floor), ("ptau_floor", ptau_floor)):
        if key in pre and float(pre[key]) != value:
            raise CardError(f"ad_like_v1.yaml: {key} does not agree with the formula")
    columns = (card.get("source") or {}).get("columns") or {}
    if not columns.get("abeta") or not columns.get("ptau"):
        raise CardError("ad_like_v1.yaml: source columns for abeta and ptau are not defined")
    return {"abeta_cap": abeta_cap, "abeta_floor": abeta_floor, "ptau_floor": ptau_floor, "cutoff": float(rule["cutoff"]),
            "abeta_column": columns["abeta"], "ptau_column": columns["ptau"],
            "abeta_flags": abeta_flags, "ptau_flags": ptau_flags}


def _flagged(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise CardError(f"ad_like_v1.yaml names the limit flag {column}, which is not a column of the curated cut")
    return pd.to_numeric(frame[column], errors="coerce") == 1


def ad_like_values(frame: pd.DataFrame, params: dict) -> pd.DataFrame:
    """``abeta_used``, ``ptau_used``, ``ratio`` and where each value came from, exactly as on the card.

    A numeric value is clamped to the assay limits; a missing value with a
    limit flag gets the boundary value (a boundary substitution for a censored
    measurement); anything else is missing. A numeric value <= 0 is not a
    measurement and is treated as missing. ``censored`` is True when either
    value used is a boundary substitution (from a flag, or a numeric value at
    or beyond a limit).
    """
    a = pd.to_numeric(frame[params["abeta_column"]], errors="coerce")
    p = pd.to_numeric(frame[params["ptau_column"]], errors="coerce")
    a, p = a.where(a > 0), p.where(p > 0)
    lo, hi, floor = params["abeta_floor"], params["abeta_cap"], params["ptau_floor"]
    abeta_used, ptau_used = a.clip(lower=lo, upper=hi), p.clip(lower=floor)
    out = pd.DataFrame(index=frame.index)
    for prefix, used, measured, flags in (("abeta", abeta_used, a, params["abeta_flags"]),
                                          ("ptau", ptau_used, p, params["ptau_flags"])):
        from_flag = pd.Series(False, index=frame.index)
        for column, value in flags.items():  # in the card's order: an earlier branch wins
            hit = measured.isna() & _flagged(frame, column) & ~from_flag
            used, from_flag = used.where(~hit, value), from_flag | hit
            out[f"{prefix}_from_{column}"] = hit
        out[f"{prefix}_used"], out[f"{prefix}_from_flag"] = used, from_flag
    out["abeta_clamped"] = a.notna() & ((a <= lo) | (a >= hi))
    out["ptau_clamped"] = p.notna() & (p <= floor)
    out["valid"] = out["abeta_used"].notna() & out["ptau_used"].notna()
    out["ratio"] = (out["ptau_used"] / out["abeta_used"]).where(out["valid"])
    out["censored"] = out["valid"] & (out["abeta_from_flag"] | out["ptau_from_flag"] | out["abeta_clamped"] | out["ptau_clamped"])
    return out


def ad_like(frame: pd.DataFrame, card: dict) -> dict[str, pd.Series]:
    """The primary label and every Elecsys sensitivity variant listed on the card (same limit rules for all)."""
    params = ad_like_parameters(card)
    values = ad_like_values(frame, params)
    ratio, valid = values["ratio"], values["valid"]
    name = card_label(card)
    labels = {name: _tri(ratio > params["cutoff"], valid)}
    for variant in card.get("sensitivity_variants") or []:
        vid, rule = str(variant["id"]), str(variant.get("rule", ""))
        if not vid.startswith(name + "_"):
            continue  # a separate card (for example the Lumipulse replication)
        band = re.search(r"\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]", rule)
        cut = re.search(r"ratio\s*>\s*([0-9.]+)", rule)
        amyloid = re.search(r"abeta_used\s*<=\s*([0-9.]+)", rule)
        if band and cut:
            low, high = float(band.group(1)), float(band.group(2))
            labels[vid] = _tri(ratio > float(cut.group(1)), valid & ~ratio.between(low, high))
        elif cut and "boundary substitution" in rule:
            labels[vid] = _tri(ratio > float(cut.group(1)), valid & ~values["censored"])
        elif cut:
            labels[vid] = _tri(ratio > float(cut.group(1)), valid)
        elif amyloid:
            labels[vid] = _tri(values["abeta_used"] <= float(amyloid.group(1)), values["abeta_used"].notna())
        else:
            raise CardError(f"ad_like_v1.yaml: sensitivity variant {vid} has a rule the builder cannot read")
    return labels


def ad_like_limit_counts(frame: pd.DataFrame, card: dict) -> dict[str, int]:
    """How many participants have a boundary substitution for a censored measurement (aggregate, for the report)."""
    params = ad_like_parameters(card)
    v = ad_like_values(frame, params)
    valid = v["valid"]
    counts = {"participants with a valid Elecsys ratio (eligible)": int(valid.sum())}
    for prefix, flags in (("abeta", params["abeta_flags"]), ("ptau", params["ptau_flags"])):
        for column, value in flags.items():
            counts[f"eligible: {prefix} boundary substitution {value:g} from flag {column}"] = int((valid & v[f"{prefix}_from_{column}"]).sum())
        counts[f"eligible: {prefix} numeric value at or beyond a limit (clamped)"] = int((valid & v[f"{prefix}_clamped"]).sum())
    counts["eligible: abeta or ptau is a boundary substitution (ad_like_v1_censored = 1)"] = int(v["censored"].sum())
    counts["eligible: both abeta and ptau are boundary substitutions"] = int(
        (valid & (v["abeta_from_flag"] | v["abeta_clamped"]) & (v["ptau_from_flag"] | v["ptau_clamped"])).sum())
    counts["masked: abeta or ptau missing without a limit flag, non-numeric or <= 0"] = int((~valid).sum())
    return counts


# --------------------------------------------------------------------------
# AD-like (Lumipulse)
# --------------------------------------------------------------------------

def lumipulse_ratio(abeta42: pd.Series, abeta40: pd.Series) -> pd.Series:
    a42, a40 = pd.to_numeric(abeta42, errors="coerce"), pd.to_numeric(abeta40, errors="coerce")
    return (a42 / a40).where((a42 > 0) & (a40 > 0))


def fit_lumipulse_threshold(dev_ratio: pd.Series, seed: int, n_init: int = 5, min_n: int = 30) -> dict:
    """Fit the 2-component mixture on development-set ratios and return the frozen parameters."""
    from sklearn.mixture import GaussianMixture

    values = np.log(dev_ratio.dropna().to_numpy(dtype=float)).reshape(-1, 1)
    if len(values) < min_n:
        raise CardError("too few eligible development-set participants to fit the Lumipulse mixture")
    model = GaussianMixture(n_components=2, random_state=seed, n_init=n_init).fit(values)
    means = model.means_.ravel()
    low, high = sorted(range(2), key=lambda i: means[i])
    grid = np.linspace(means[low], means[high], 20001).reshape(-1, 1)
    diff = model.predict_proba(grid)[:, low] - 0.5
    crossing = np.where(np.diff(np.sign(diff)) != 0)[0]
    if len(crossing) == 0:
        raise CardError("the Lumipulse mixture has no equal-posterior point between its component means")
    i = crossing[0]
    x0, x1, d0, d1 = grid[i, 0], grid[i + 1, 0], diff[i], diff[i + 1]
    log_threshold = float(x0 - d0 * (x1 - x0) / (d1 - d0))
    return {
        "label": "ad_like_lumipulse_v1", "fitted_on": "eligible development-set participants only",
        "n_development_participants": int(len(values)), "seed": int(seed), "n_init": int(n_init),
        "scale": "natural log of ABeta42/ABeta40",
        "component_means_log": [float(means[low]), float(means[high])],
        "component_variances_log": [float(model.covariances_.ravel()[low]), float(model.covariances_.ravel()[high])],
        "component_weights": [float(model.weights_[low]), float(model.weights_[high])],
        "threshold_log_ratio": log_threshold, "threshold_ratio": float(np.exp(log_threshold)),
        "direction": "positive if ratio < threshold_ratio (low ABeta42/ABeta40 = amyloid-positive)",
    }


def ad_like_lumipulse(ratio: pd.Series, frozen: dict) -> pd.Series:
    return _tri(ratio < float(frozen["threshold_ratio"]), ratio.notna())


# --------------------------------------------------------------------------
# Vascular
# --------------------------------------------------------------------------

def vascular(count: pd.Series, htn_evaluable: pd.Series, card: dict) -> pd.Series:
    """Positive at or above the card's component count; masked only when the unknown HTN component could change the result.

    When HTN is not evaluable the count holds DM + DYSLIP only. The label is
    then positive if that already reaches the threshold, negative if one more
    component could not reach it, and masked otherwise.
    """
    need = int(card["rule"]["min_components"])
    positive = count >= need
    out_of_reach = count + 1 < need
    return _tri(positive, positive | out_of_reach | htn_evaluable.astype(bool))
