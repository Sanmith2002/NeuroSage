"""NACC participant-level feature engineering: an exact port of Stage 2a (spec §5).

Pure, deterministic functions. The output vector is always ordered by bundle["features"];
nothing here hardcodes feature order.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .schemas import SYMPTOM_KEYS, VASCULAR_KEYS, ClinicalRequest

NaN = float('nan')

# Monsell et al. 2016, Alzheimer Dis Assoc Disord 30(2):134–139, Table 3. MoCA is already education-adjusted.
MOCA_TO_MMSE = {0: 6, 1: 9, 2: 10, 3: 11, 4: 12, 5: 12, 6: 13, 7: 14, 8: 15, 9: 15, 10: 16, 11: 17, 12: 18, 13: 19, 14: 20,
                15: 21, 16: 22, 17: 23, 18: 24, 19: 25, 20: 26, 21: 27, 22: 28, 23: 28, 24: 29, 25: 29, 26: 29, 27: 30,
                28: 30, 29: 30, 30: 30}

SYMPTOM_VARS = ['BEVHALL', 'BEREM', 'COGFLUC', 'MOSLOW', 'MOTREM', 'MOGAIT', 'MOFALLS', 'PARKSIGN', 'HALL', 'NITE', 'DEL']
VASCULAR_VARS = ['HYPERTEN_present', 'HYPERCHO_present', 'DIABETES_present', 'CBSTROKE_present', 'CBTIA_present',
                 'CVAFIB_present']
RACE_VARS = ['race_white', 'race_black', 'race_asian', 'race_other']
LAST_VARS = (['NACCAGE', 'female', 'EDUC', 'HISPANIC', 'NACCNE4S', 'NACCFAM', 'MMSE_EQ', 'NACCMMSE', 'NACCMOCA',
              'CDRSUM', 'CDRGLOB', 'NACCGDS', 'NACCBMI', 'BPSYS'] + SYMPTOM_VARS + VASCULAR_VARS + RACE_VARS)
TREND_VARS = ['MMSE_EQ', 'CDRSUM', 'NACCGDS']
SLOPE_MIN_VISITS, SLOPE_MIN_SPAN_Y = 3, 1.0

CSF_WARNING = 'CSF is used as entered; results across assays are not harmonised.'


@dataclass
class Engineered:
    features: dict[str, float]                        # name → value (NaN when missing)
    visits: pd.DataFrame                              # visit-level NACC variables (for the harmonisation table)
    harmonisation_log: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _f(v) -> float:
    return NaN if v is None else float(v)


def _b(v) -> float:
    return NaN if v is None else (1.0 if v else 0.0)


def _vasc(v) -> float:
    return NaN if v is None else (0.0 if v == 'absent' else 1.0)


def mmse_eq(mmse: float, moca: float) -> tuple[float, str]:
    """MMSE if given, else the Monsell crosswalk of the MoCA, else NaN."""
    if not math.isnan(mmse):
        return mmse, 'MMSE'
    if not math.isnan(moca):
        return float(MOCA_TO_MMSE[int(round(moca))]), 'MoCA→MMSE'
    return NaN, 'missing'


def visit_frame(req: ClinicalRequest) -> pd.DataFrame:
    """Spec §5.1: one row per visit (sorted by date), with the patient-level fields copied onto every visit."""
    p = req.patient
    race = {f'race_{r}': NaN for r in ['white', 'black', 'asian', 'other']}
    if p.race is not None:
        race = {f'race_{r}': float(p.race == r) for r in ['white', 'black', 'asian', 'other']}
    visits = sorted(req.visits, key=lambda v: v.date)
    first = visits[0].date
    rows = []
    for v in visits:
        row = {
            'date': v.date, 't_years': (v.date - first).days / 365.25,
            'NACCAGE': float(v.age),
            'female': NaN if p.sex is None else float(p.sex == 'female'),
            'EDUC': _f(p.education_years), 'HISPANIC': _b(p.hispanic),
            'NACCNE4S': _f(p.apoe_e4_count), 'NACCFAM': _b(p.family_history),
            'NACCMMSE': _f(v.mmse), 'NACCMOCA': _f(v.moca),
            'CDRGLOB': _f(v.cdr_global), 'CDRSUM': _f(v.cdr_sum), 'NACCGDS': _f(v.gds),
            'NACCBMI': _f(v.bmi), 'BPSYS': _f(v.bp_systolic),
            'cog_untestable': 1.0 if v.cognition_untestable else 0.0,
        }
        for key, var in zip(SYMPTOM_KEYS, SYMPTOM_VARS):
            row[var] = _b(getattr(v.symptoms, key))
        for key, var in zip(VASCULAR_KEYS, VASCULAR_VARS):
            row[var] = _vasc(getattr(v.vascular, key))
        row.update(race)
        row['MMSE_EQ'], row['MMSE_EQ_SOURCE'] = mmse_eq(row['NACCMMSE'], row['NACCMOCA'])
        rows.append(row)
    return pd.DataFrame(rows)


def _max_or_nan(s: pd.Series) -> float:
    s = s.dropna()
    return float(s.max()) if len(s) else NaN


def _slope(t: pd.Series, y: pd.Series) -> float:
    ok = y.notna()
    if ok.sum() < SLOPE_MIN_VISITS:
        return NaN
    tt, yy = t[ok].to_numpy(float), y[ok].to_numpy(float)
    if tt.max() - tt.min() < SLOPE_MIN_SPAN_Y:
        return NaN
    return float(np.polyfit(tt, yy, 1)[0])


def _pos(v) -> float:
    return NaN if v is None or v <= 0 else float(v)


def participant_features(V: pd.DataFrame, csf=None) -> dict[str, float]:
    """Spec §5.3: the participant-level features from the visit frame."""
    last, first = V.iloc[-1], V.iloc[0]
    F: dict[str, float] = {}
    for x in LAST_VARS:
        F[f'last_{x}'] = float(last[x])                  # value at the last row, even if NaN: no carry-forward
    for x in SYMPTOM_VARS:
        F[f'ever_{x}'] = _max_or_nan(V[x])

    avail = V[V.MMSE_EQ.notna()]
    if len(avail):
        F['lastavail_MMSE_EQ'] = float(avail.MMSE_EQ.iloc[-1])
        F['years_since_MMSE_EQ'] = max(0.0, float(last.t_years - avail.t_years.iloc[-1]))
    else:
        F['lastavail_MMSE_EQ'] = F['years_since_MMSE_EQ'] = NaN

    F['last_cog_untestable'] = float(last.cog_untestable)
    F['ever_cog_untestable'] = float(V.cog_untestable.max())
    F['n_visits'] = float(len(V))
    F['followup_years'] = float(V.t_years.max())
    F['age_first_visit'] = float(first.NACCAGE)
    for y in TREND_VARS:
        F[f'slope_{y}'] = _slope(V.t_years, V[y])
        F[f'delta_{y}'] = float(last[y] - first[y])      # NaN propagates if either end is NaN
    F['missing_NACCGDS'] = 1.0 if math.isnan(F['last_NACCGDS']) else 0.0

    ab = _pos(csf.abeta42) if csf else NaN
    pt = _pos(csf.ptau181) if csf else NaN
    tt = _pos(csf.ttau) if csf else NaN
    F['csf_abeta'], F['csf_ptau'], F['csf_ttau'] = ab, pt, tt
    F['csf_ptau_abeta'] = pt / ab if not (math.isnan(pt) or math.isnan(ab)) else NaN
    F['csf_ttau_abeta'] = tt / ab if not (math.isnan(tt) or math.isnan(ab)) else NaN
    F['has_csf'] = 0.0 if all(math.isnan(v) for v in (ab, pt, tt)) else 1.0
    return F


def engineer(req: ClinicalRequest) -> Engineered:
    V = visit_frame(req)
    F = participant_features(V, req.csf)
    log: list[dict] = []
    for _, r in V.iterrows():
        d = r.date.isoformat()
        if r.MMSE_EQ_SOURCE == 'MoCA→MMSE':
            log.append({'visit': d, 'original': f'MoCA {r.NACCMOCA:g}', 'standard': f'MMSE_EQ {r.MMSE_EQ:g}',
                        'rule': 'Monsell 2016 crosswalk'})
        elif r.MMSE_EQ_SOURCE == 'MMSE':
            log.append({'visit': d, 'original': f'MMSE {r.NACCMMSE:g}', 'standard': f'MMSE_EQ {r.MMSE_EQ:g}',
                        'rule': 'MMSE used directly'})
        else:
            log.append({'visit': d, 'original': 'untestable' if r.cog_untestable else 'no MMSE/MoCA',
                        'standard': 'MMSE_EQ missing', 'rule': 'left missing; the model imputes'})
    warnings: list[str] = []
    if F['has_csf'] == 1.0:
        warnings.append(CSF_WARNING)
    if len(V) < SLOPE_MIN_VISITS or F['followup_years'] < SLOPE_MIN_SPAN_Y:
        warnings.append('Trend features (slopes) need ≥ 3 visits spanning ≥ 1 year; they are missing for this patient.')
    return Engineered(F, V, log, warnings)


def to_frame(F: dict[str, float], features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Orders the vector by the bundle's feature list. Features the engineering does not produce become NaN."""
    missing = [c for c in features if c not in F]
    row = {c: F.get(c, NaN) for c in features}
    return pd.DataFrame([row], columns=features, dtype=float), missing
