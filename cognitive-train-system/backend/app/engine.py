
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

DOM = ["memory", "attention", "visuospatial", "executive", "language"]

# test -> domain map (UDS v3); must match the training notebooks exactly
NEURO = {
    "memory":       ["CRAFTVRS", "CRAFTURS", "CRAFTDVR", "CRAFTDRE", "UDSBENTD"],
    "attention":    ["DIGFORCT", "DIGFORSL", "DIGBACCT", "DIGBACLS", "TRAILA"],
    "executive":    ["TRAILB", "UDSVERFC", "UDSVERLC", "UDSVERTN"],
    "language":     ["MINTTOTS", "ANIMALS", "VEG"],
    "visuospatial": ["UDSBENTC"],
}
RANGES = {
    "CRAFTVRS": (0, 44), "CRAFTURS": (0, 25), "CRAFTDVR": (0, 44), "CRAFTDRE": (0, 25),
    "UDSBENTD": (0, 17), "UDSBENTC": (0, 17),
    "DIGFORCT": (0, 14), "DIGFORSL": (0, 9), "DIGBACCT": (0, 14), "DIGBACLS": (0, 8),
    "TRAILA": (0, 150), "TRAILB": (0, 300),
    "UDSVERFC": (0, 40), "UDSVERLC": (0, 40), "UDSVERTN": (0, 80),
    "MINTTOTS": (0, 32), "ANIMALS": (0, 77), "VEG": (0, 77),
}
FLIP = {"TRAILA", "TRAILB"}

# adapter (integration contract)
LABELS = ["alzheimer", "parkinson", "vascular", "lbd"]
ARM_MAP = {"alzheimer": "AD", "lbd": "LBD", "parkinson": "LBD", "vascular": "FALLBACK"}
CONF_MIN, MARGIN_MIN = 0.50, 0.15          # routing gate (documented; NOT the weakness threshold)

WEAK_THRESHOLD = -1.0                        # cited clinical convention (fixed)
W_DECLINE = 0.3                              # data-driven default from Step 5 (configurable)


class Engine:
    def __init__(self, models_dir: str):
        md = Path(models_dir)
        self.reference = json.loads((md / "zscore_reference.json").read_text(encoding="utf-8"))
        bundle = joblib.load(md / "decline_models.joblib")
        self.models = bundle["models"]                      # {(arm, domain): fitted estimator}
        self.feat = list(bundle["features"])                # base_<dom> + age + education + sex01
        self.fallback = {tuple(x) for x in bundle["fallback"]}
        self.catalog = json.loads((md / "exercise_catalog.json").read_text(encoding="utf-8"))["exercises"]

    # ---- measurement: raw UDS v3 test scores -> per-domain z ----
    def tests_to_domain_z(self, raw: dict) -> dict:
        tz = {}
        for t, r in self.reference.items():
            v = raw.get(t)
            if v is None or r["sd"] <= 0:
                continue
            lo, hi = RANGES[t]
            if lo <= v <= hi:                                # recode out-of-range to missing
                z = (v - r["mean"]) / r["sd"]
                tz[t] = -z if not r["higher_is_better"] else z   # flip Trails
        dz = {}
        for d, cols in NEURO.items():
            vals = [tz[c] for c in cols if c in tz]
            dz[d] = float(np.mean(vals)) if vals else None
        return dz

    # ---- adapter: 4-label probabilities -> arm or FALLBACK ----
    def route(self, probs) -> dict:
        if isinstance(probs, dict):
            d = {str(k).strip().lower(): v for k, v in probs.items()}
            if set(d) != set(LABELS):
                raise ValueError(f"labels {sorted(d)} != required {LABELS}")
            vals = [d[l] for l in LABELS]
        elif isinstance(probs, (list, tuple)):
            if len(probs) != 4:
                raise ValueError(f"expected 4 values in order {LABELS}")
            vals = list(probs)
        else:
            raise ValueError("probabilities must be a dict or a list of 4")
        v = np.array(vals, float)
        if not np.isfinite(v).all() or (v < 0).any() or v.sum() <= 0:
            raise ValueError("probabilities must be finite, non-negative, and sum > 0")
        v = v / v.sum()
        order = v.argsort()[::-1]
        top, second = LABELS[order[0]], LABELS[order[1]]
        top_p, margin = float(v[order[0]]), float(v[order[0]] - v[order[1]])
        tag = f"(top {top}={top_p:.2f}, margin {margin:.2f})"
        if top_p < CONF_MIN or margin < MARGIN_MIN:
            return {"route": "FALLBACK", "arm": None, "routing_reason": "low_confidence",
                    "reason": f"low confidence {tag} -> safe fallback"}
        if ARM_MAP[top] == "FALLBACK":
            return {"route": "FALLBACK", "arm": None, "routing_reason": "out_of_scope",
                    "reason": f"{top} out of scope {tag} -> safe fallback"}
        rr = "parkinson_proxy" if top == "parkinson" else "direct"
        note = " (provisional Lewy-body-spectrum proxy; not a PDD / diagnosis confirmation)" if top == "parkinson" else ""
        return {"route": ARM_MAP[top], "arm": ARM_MAP[top], "routing_reason": rr,
                "reason": f"{top} {tag} -> {ARM_MAP[top]} arm{note}"}

    # ---- decline: per-domain predicted severity for one patient ----
    def predict_decline(self, arm: str, dz: dict, age, education, sex) -> dict:
        row = {"base_" + d: (dz[d] if dz[d] is not None else np.nan) for d in DOM}
        row["age"] = age if age is not None else np.nan
        row["education"] = education if education is not None else np.nan
        row["sex01"] = {"M": 1, "F": 0}.get(sex, np.nan)
        X = pd.DataFrame([row])[self.feat]
        sev = {}
        for d in DOM:
            pred = float(self.models[(arm, d)].predict(X)[0])
            sev[d] = max(0.0, -pred)                         # severity = max(0, -slope)
        return sev

    # ---- SAW: within-patient min-max, per-domain weight renormalisation ----
    def saw(self, weaknow: dict, willworsen: dict, w_dec=W_DECLINE) -> dict:
        w_now = 1 - w_dec
        wn = np.array([weaknow[d] for d in DOM], float)
        ww = np.array([willworsen.get(d, np.nan) for d in DOM], float)
        rng = np.nanmax(wn) - np.nanmin(wn)
        nNOW = (wn - np.nanmin(wn)) / rng if rng > 0 else np.zeros(len(DOM))
        hasd = ~np.isnan(ww)
        nDEC = np.full(len(DOM), np.nan)
        if hasd.sum() >= 2 and np.nanmax(ww[hasd]) != np.nanmin(ww[hasd]):
            lo, hi = np.nanmin(ww[hasd]), np.nanmax(ww[hasd])
            nDEC[hasd] = (ww[hasd] - lo) / (hi - lo)
        hd = ~np.isnan(nDEC)
        score = (w_now * nNOW + np.where(hd, w_dec * np.nan_to_num(nDEC), 0.0)) / (w_now + np.where(hd, w_dec, 0.0))
        return {DOM[i]: float(score[i]) for i in range(len(DOM))}

    def pick_exercise(self, domain: str, arm: str) -> dict:
        cands = [e for e in self.catalog if e["domain"] == domain]
        cands.sort(key=lambda e: (arm in e["arm_emphasis"], e["expected_benefit_g"]), reverse=True)
        return cands[0]

    # ---- the full recommendation ----
    def recommend(self, probs, domain_z: dict, age=None, education=None, sex=None, top_k=3) -> dict:
        routed = self.route(probs)
        if routed["route"] == "FALLBACK":
            return {"route": "FALLBACK", "reason": routed["reason"],
                    "message": "Diagnosis input inconclusive or out of scope -> general (non-personalised) plan.",
                    "plan": [{"domain": d, "exercise": self.pick_exercise(d, "AD")["name"]} for d in DOM]}
        arm = routed["arm"]
        weaknow = {d: (-domain_z[d] if domain_z.get(d) is not None else np.nan) for d in DOM}
        willworsen = self.predict_decline(arm, domain_z, age, education, sex)
        score = self.saw(weaknow, willworsen)
        order = sorted(DOM, key=lambda d: score[d], reverse=True)
        plan = []
        for d in order[:top_k]:
            ex = self.pick_exercise(d, arm)
            is_weak = (domain_z.get(d) is not None) and (domain_z[d] <= WEAK_THRESHOLD)
            worsening = willworsen[d] > 0
            if is_weak and worsening:
                why = "weak now + predicted decline -> high priority"
            elif is_weak:
                why = "weak now -> priority"
            elif worsening:
                why = "not weak now but predicted decline -> preventive"
            else:
                why = "relative priority"
            plan.append({
                "domain": d,
                "score": round(score[d], 3),
                "is_weak": is_weak,
                "will_worsen": round(willworsen[d], 3),
                "exercise_id": ex["id"],
                "exercise": ex["name"],
                "strategy": ex["strategy"],
                "expected_benefit_g": ex["expected_benefit_g"],
                "low_benefit": ex["expected_benefit_g"] < 0.30,
                "language_dependency": ex["language_dependency"],
                "reason": why,
            })
        return {"route": arm, "arm": arm, "routing_reason": routed["routing_reason"],
                "reason": routed["reason"], "plan": plan}
