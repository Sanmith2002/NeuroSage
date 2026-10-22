"""NACC clinical co-pathology: prediction, fold uncertainty, SHAP and the reliability signals (spec §5.5)."""
from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .features import Engineered, to_frame
from .form_spec import display_name
from .registry import Registry

LABELS = {'y_AD': "Alzheimer's disease", 'y_LBD': 'Lewy body pathology', 'y_VD': 'Vascular pathology'}
KEY_FEATURES = ['last_NACCNE4S', 'lastavail_MMSE_EQ', 'last_CDRSUM', 'ever_BEVHALL', 'ever_BEREM', 'last_NACCAGE',
                'last_CBSTROKE_present', 'last_NACCBMI']
TOP_K = 8
SD_SCALE, MARGIN_SCALE = 0.15, 0.10

# Thesis-reported locked-test results (spec §2.1). Used when model_card.json is absent or lacks a value.
REPORTED = {
    'RandomForest': {
        'y_AD': dict(test_auroc=0.813, test_auroc_ci=[0.785, 0.841], test_auprc=0.905, test_bacc=0.747, test_ece=0.033),
        'y_LBD': dict(test_auroc=0.700, test_auroc_ci=[0.662, 0.740], test_auprc=0.469, test_bacc=0.644, test_ece=0.022),
        'y_VD': dict(test_auroc=0.675, test_auroc_ci=[0.641, 0.707], test_auprc=0.463, test_bacc=0.635, test_ece=0.025),
    },
}
STABILITY = {'y_AD': (0.93, 0.65), 'y_LBD': (0.89, 0.65), 'y_VD': (0.84, 0.75)}   # Spearman, top-10 Jaccard
MODEL_IDS = {'RandomForest': 'NACC-RandomForest-5fold', 'XGBoost': 'NACC-XGBoost-5fold'}


@dataclass
class ClinicalResult:
    model_key: str
    model_name: str
    labels: list[dict]
    signals: dict[str, dict | None]
    features: dict[str, float]
    warnings: list[str] = field(default_factory=list)
    timings_s: dict[str, float] = field(default_factory=dict)


# ------------------------------------------------------------------ helpers
def _num(v) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def _split_pipeline(est):
    """RF folds are Pipeline(imp → m); XGB folds are bare estimators."""
    if hasattr(est, 'steps'):
        return est[:-1], est[-1]
    return None, est


def _positive_class(sv) -> np.ndarray:
    """Normalises shap output across shap versions to (n_rows, n_features) for the positive class."""
    if isinstance(sv, list):
        return np.asarray(sv[1])
    sv = np.asarray(sv)
    return sv[..., 1] if sv.ndim == 3 else sv


def fold_raw(bundle: dict, X: pd.DataFrame) -> dict[str, np.ndarray]:
    """Raw (uncalibrated) positive-class probability of every fold model → (n_folds,) per label, for one row."""
    return {L: np.array([fold[j].predict_proba(X)[:, 1][0] for fold in bundle['folds']])
            for j, L in enumerate(bundle['targets'])}


def calibrated(bundle: dict, raw: dict[str, np.ndarray]) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    """Same arithmetic as model_defs.predict_nacc (mean of folds → Platt), computed from one pass over the forests,
    plus each fold's own calibrated probability for the uncertainty estimate."""
    probs, folds = {}, {}
    for L in bundle['targets']:
        cal = bundle['calibrators'][L]
        probs[L] = float(cal.predict(np.array([raw[L].mean()]))[0])
        folds[L] = cal.predict(raw[L])
    return probs, folds


def fold_probabilities(bundle: dict, X: pd.DataFrame) -> dict[str, np.ndarray]:
    """Each fold's raw probability passed through that label's calibrator → (n_folds,) per label."""
    return calibrated(bundle, fold_raw(bundle, X))[1]


_shap_cache: OrderedDict[str, dict] = OrderedDict()
_shap_lock = threading.Lock()


def shap_values(bundle: dict, X: pd.DataFrame, cache_size: int = 256) -> tuple[dict[str, dict[str, float]], str]:
    """Mean TreeSHAP over the 5 folds, per label, keyed by base feature.

    RF: explain the forest on the imputed matrix and fold each `missingindicator_<f>` back onto <f>.
    XGB: explain directly (NaN handled natively). Scale: probability (RF) or log-odds (XGB)."""
    import shap

    feats = list(bundle['features'])
    key = hashlib.sha256((bundle['model_name'] + json.dumps(X.iloc[0].tolist(), default=str)).encode()).hexdigest()
    with _shap_lock:
        if key in _shap_cache:
            _shap_cache.move_to_end(key)
            return _shap_cache[key]['values'], _shap_cache[key]['scale']

    scale = 'log-odds'
    out: dict[str, dict[str, float]] = {}
    for j, L in enumerate(bundle['targets']):
        acc = np.zeros(len(feats))
        for fold in bundle['folds']:
            pre, m = _split_pipeline(fold[j])
            if pre is None:
                sv = _positive_class(shap.TreeExplainer(m).shap_values(X, check_additivity=False))[0]
                acc += sv
                continue
            scale = 'probability'
            Xt = pre.transform(X)
            names = list(pre.get_feature_names_out(feats))
            sv = _positive_class(shap.TreeExplainer(m).shap_values(Xt, check_additivity=False))[0]
            idx = {f: i for i, f in enumerate(feats)}
            for name, v in zip(names, sv):
                base = name.removeprefix('missingindicator_')
                if base in idx:
                    acc[idx[base]] += v
        acc /= len(bundle['folds'])
        out[L] = dict(zip(feats, acc.tolist()))

    with _shap_lock:
        _shap_cache[key] = {'values': out, 'scale': scale}
        while len(_shap_cache) > cache_size:
            _shap_cache.popitem(last=False)
    return out, scale


def _card_performance(reg: Registry, model_name: str, L: str) -> dict:
    perf = dict(REPORTED.get(model_name, {}).get(L, {}))
    card = (reg.model_card or {}).get('nacc', {}).get(model_name, {}).get(L)
    if card:
        perf.update({k: v for k, v in dict(test_auroc=card.get('AUROC'), test_auprc=card.get('AUPRC'),
                                            test_bacc=card.get('BACC'), test_ece=card.get('ECE'),
                                            test_sens=card.get('sens'), test_spec=card.get('spec'),
                                            n_test=card.get('n_test')).items() if v is not None})
    return perf


def _card_stability(reg: Registry, L: str) -> float:
    """Global fold-stability Spearman for a label; model_card.json overrides the spec values when present."""
    for rec in (reg.model_card or {}).get('explanation_stability') or []:
        lab = next((v for k, v in rec.items() if k.lower() in {'label', 'target'}), None)
        if lab in (L, L.removeprefix('y_')):
            sp = next((v for k, v in rec.items() if 'spearman' in k.lower() and isinstance(v, (int, float))), None)
            if sp is not None:
                return float(sp)
    return STABILITY[L][0]


# ------------------------------------------------------------------ reliability signals
def distribution_conformity(reg: Registry, X: pd.DataFrame) -> dict | None:
    if reg.ood is None:
        return None
    ood = reg.ood
    x = X[ood['features']] if all(f in X for f in ood['features']) else X.reindex(columns=ood['features'])
    d = float(ood['detector'].mahalanobis(ood['pre'].transform(x))[0])
    q = np.asarray(ood['ref_quantiles'], float)
    pct = float(np.interp(d, q, np.arange(len(q)) * (100.0 / (len(q) - 1))))
    detail = f'Mahalanobis percentile {pct:.0f} among development cases (experimental)'
    if pct > 99:
        detail += ' — flagged: more unusual than 99% of training cases'
    return {'score': round(1 - pct / 100, 4), 'detail': detail, 'percentile': round(pct, 1), 'flagged': pct > 99,
            'experimental': True}


def domain_familiarity(reg: Registry, F: dict[str, float]) -> tuple[dict | None, list[str]]:
    if reg.feature_stats is None:
        return None, []
    stats = reg.feature_stats['features']
    present, outside = 0, []
    for f, v in F.items():
        s = stats.get(f)
        if s is None or v is None or math.isnan(v) or s.get('p1') is None:
            continue
        present += 1
        if v < s['p1'] or v > s['p99']:
            outside.append(f)
    score = 1 - len(outside) / present if present else 0.0
    names = ', '.join(display_name(f) for f in outside[:5]) + ('…' if len(outside) > 5 else '')
    detail = (f'{len(outside)} feature(s) outside training p1–p99: {names}' if outside
              else 'All entered values lie within the training p1–p99 range')
    return {'score': round(score, 4), 'detail': detail, 'outside': outside}, outside


def data_sufficiency(F: dict[str, float]) -> dict:
    present = [f for f in KEY_FEATURES if F.get(f) is not None and not math.isnan(F[f])]
    score = len(present) / len(KEY_FEATURES)      # equal weights: no global SHAP importance ships with the bundles
    missing = [display_name(f) for f in KEY_FEATURES if f not in present]
    detail = f'{len(present)}/{len(KEY_FEATURES)} key inputs present'
    if missing:
        detail += f' (missing: {", ".join(missing)})'
    if F.get('n_visits', 0) < 3:
        detail += '; slopes need ≥ 3 visits'
    return {'score': round(score, 4), 'detail': detail, 'missing': missing}


def prediction_certainty(labels: list[dict]) -> dict:
    """Placeholder formula from spec §7, until the Safety component defines its own."""
    sds = [l['uncertainty']['fold_sd'] for l in labels]
    margins = [l['uncertainty']['margin'] for l in labels]
    score = float(np.mean([1 - min(1.0, s / SD_SCALE) for s in sds]) * min(1.0, min(margins) / MARGIN_SCALE))
    return {'score': round(score, 4), 'detail': f'mean fold SD {np.mean(sds):.3f}; min margin to threshold {min(margins):.3f}'}


# ------------------------------------------------------------------ main entry
def predict(reg: Registry, eng: Engineered, model: str = 'auto', explain: bool = True,
            shap_cache_size: int = 256) -> ClinicalResult:
    t0 = time.perf_counter()
    key = reg.active_nacc() if model == 'auto' else model
    bundle = reg.get_nacc(key)
    X, missing = to_frame(eng.features, list(bundle['features']))
    warnings = list(eng.warnings)
    if missing:
        warnings.append(f'{len(missing)} model feature(s) not produced by the form and left missing: {", ".join(missing)}')

    probs, folds = calibrated(bundle, fold_raw(bundle, X))
    timings = {'predict': round(time.perf_counter() - t0, 3)}

    shap_vals, scale = (None, None)
    if explain:
        t1 = time.perf_counter()
        shap_vals, scale = shap_values(bundle, X, shap_cache_size)
        timings['shap'] = round(time.perf_counter() - t1, 3)

    model_name = bundle['model_name']
    labels = []
    for L in bundle['targets']:
        p, thr = probs[L], float(bundle['thresholds'][L])
        entry = {
            'key': L, 'label': LABELS.get(L, L), 'probability': round(p, 6), 'threshold': round(thr, 6),
            'predicted': p >= thr,
            'uncertainty': {'fold_mean': round(float(folds[L].mean()), 6), 'fold_sd': round(float(folds[L].std()), 6),
                            'margin': round(abs(p - thr), 6)},
            'calibration': {'method': 'platt', 'test_ece': _card_performance(reg, model_name, L).get('test_ece')},
            'performance': _card_performance(reg, model_name, L),
            'source': 'clinical',
        }
        if shap_vals is not None:
            sv = shap_vals[L]
            top = sorted(sv.items(), key=lambda kv: -abs(kv[1]))[:TOP_K]
            entry['explanation'] = {
                'method': 'shap', 'scale': scale, 'stability_spearman': _card_stability(reg, L),
                'stability_jaccard_top10': STABILITY[L][1],
                'top': [{'feature': f, 'display_name': display_name(f), 'value': _num(eng.features.get(f)),
                         'shap': round(v, 6), 'direction': 'supports' if v > 0 else 'reduces'} for f, v in top],
            }
        labels.append(entry)

    conformity = distribution_conformity(reg, X)
    familiarity, _ = domain_familiarity(reg, eng.features)
    stab = [_card_stability(reg, L) for L in bundle['targets']]
    signals = {
        'dataSufficiency': data_sufficiency(eng.features),
        'distributionConformity': conformity,
        'predictionCertainty': prediction_certainty(labels),
        'modalityAgreement': None,
        'domainFamiliarity': familiarity,
        'explanationReliability': {'score': round(float(np.mean(stab)), 4),
                                   'detail': 'global fold-stability (Spearman) per label: '
                                             + ', '.join(f'{LABELS[L].split()[0]} {s:.2f}' for L, s in zip(bundle['targets'], stab))},
        'clinicalHarmRisk': None,
    }
    if conformity is None:
        warnings.append('Distribution-conformity detector (ood_nacc.joblib) not loaded; signal unavailable.')
    if familiarity is None:
        warnings.append('feature_stats.json not loaded; domain-familiarity signal unavailable.')
    timings['total'] = round(time.perf_counter() - t0, 3)
    return ClinicalResult(key, model_name, labels, signals, eng.features, warnings, timings)
