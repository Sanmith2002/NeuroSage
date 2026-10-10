"""ADNI prediction with the cached torch nets, plus fusion attention and Grad-CAM (spec §6.11–13).

Numerically identical to model_defs.predict_adni (per fold: net → that fold's Platt → mean → threshold);
the only difference is that the nets are built once in the registry instead of per call.
"""
from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn.functional as Fnn

from ..registry import Registry
from ..schemas import MriFields

VOL_SHAPE = (80, 96, 80)


def tabular_vector(bundle: dict, fields: MriFields) -> np.ndarray:
    """Orders [age_at_scan, female, educ, apoe_e4] by bundle['tab_features']; NaN is imputed by the fold pipelines."""
    nan = float('nan')
    vals = {
        'age_at_scan': nan if fields.age_at_scan is None else float(fields.age_at_scan),
        'female': nan if fields.sex is None else float(fields.sex == 'female'),
        'educ': nan if fields.education_years is None else float(fields.education_years),
        'apoe_e4': nan if fields.apoe_e4_count is None else float(fields.apoe_e4_count),
    }
    missing = [f for f in bundle['tab_features'] if f not in vals]
    if missing:
        raise KeyError(f'unknown tabular features in bundle: {missing}')
    return np.array([[vals[f] for f in bundle['tab_features']]], dtype=np.float32)


def _platt(md, ab, p):
    return md.platt_apply(ab, p)


@torch.no_grad()
def predict_image_bundle(reg: Registry, key: str, x: np.ndarray, fields: MriFields) -> dict:
    bundle, nets = reg.adni[key], reg.nets[key]
    tab = tabular_vector(bundle, fields)
    xt = torch.tensor(np.asarray(x, np.float32)[None, None])
    ps, ws = [], []
    for f, net in zip(bundle['folds'], nets):
        t = torch.tensor(f['tab_pre'].transform(tab).astype(np.float32)) if bundle['kind'] == 'fusion' else None
        logit, w = net(xt, t)
        p = torch.sigmoid(logit.float()).numpy()
        ps.append(_platt(reg.model_defs, f['platt'], p))
        if w is not None:
            ws.append(w[0].numpy())
    per_fold = np.array([p[0] for p in ps])
    p = float(per_fold.mean())
    out = {'p': p, 'pred': int(p >= bundle['threshold']), 'thr': float(bundle['threshold']),
           'fold_sd': float(per_fold.std())}
    if ws:
        w = np.mean(ws, axis=0)
        out['attention'] = {'mri': round(float(w[0]), 4), 'tabular': round(float(w[1]), 4)}
    return out


def predict_tabular_bundle(reg: Registry, key: str, fields: MriFields) -> dict:
    bundle = reg.adni[key]
    tab = tabular_vector(bundle, fields)
    ps = [_platt(reg.model_defs, f['platt'], f['model'].predict_proba(tab)[:, 1]) for f in bundle['folds']]
    p = float(np.mean(ps, axis=0)[0])
    return {'p': p, 'pred': int(p >= bundle['threshold']), 'thr': float(bundle['threshold'])}


def gradcam(reg: Registry, x: np.ndarray, fields: MriFields, key: str = 'ad_clin') -> np.ndarray:
    """Fold-0 Grad-CAM, for display only: relu(Σ_c mean_grad_c · act_c), trilinear to 80×96×80, scaled to [0, 1]."""
    bundle, net = reg.adni[key], reg.nets[key][0]
    target = net.bb.net.layers[-2] if bundle['arch'] == 'SmallResNet-3D' else net.bb.net.layer3
    store: dict[str, torch.Tensor] = {}

    def fwd_hook(_m, _i, out):
        store['act'] = out
        out.register_hook(lambda g: store.__setitem__('grad', g))

    h = target.register_forward_hook(fwd_hook)
    try:
        with torch.enable_grad():
            xt = torch.tensor(np.asarray(x, np.float32)[None, None], requires_grad=True)
            f0 = bundle['folds'][0]
            t = torch.tensor(f0['tab_pre'].transform(tabular_vector(bundle, fields)).astype(np.float32)) \
                if bundle['kind'] == 'fusion' else None
            logit, _ = net(xt, t)
            logit.sum().backward()
    finally:
        h.remove()
    act, grad = store['act'].detach(), store['grad'].detach()
    weights = grad.mean(dim=(2, 3, 4), keepdim=True)
    cam = Fnn.relu((weights * act).sum(1, keepdim=True))
    cam = Fnn.interpolate(cam, size=VOL_SHAPE, mode='trilinear', align_corners=False)[0, 0].numpy()
    lo, hi = float(cam.min()), float(cam.max())
    return (cam - lo) / (hi - lo) if hi > lo else np.zeros_like(cam)


def predict_all(reg: Registry, x: np.ndarray | None, fields: MriFields) -> dict:
    """Returns the MriResult fields (without QC / artifacts)."""
    out: dict = {}
    if x is not None and 'ad_clin' in reg.adni:
        r = predict_image_bundle(reg, 'ad_clin', x, fields)
        out.update(p_ad_clin=r['p'], pred_ad_clin=r['pred'], thr_ad_clin=r['thr'], fold_sd_ad_clin=r['fold_sd'],
                   attention=r.get('attention'),
                   ad_clin_model=reg.adni['ad_clin'].get('model', reg.adni['ad_clin']['kind']))
    if 'ad_bio' in reg.adni:
        b = reg.adni['ad_bio']
        if b['kind'] == 'tabular':
            r = predict_tabular_bundle(reg, 'ad_bio', fields)
        elif x is not None:
            r = predict_image_bundle(reg, 'ad_bio', x, fields)
        else:
            r = None
        if r is not None:
            out.update(p_ad_bio=r['p'], pred_ad_bio=r['pred'], thr_ad_bio=r['thr'],
                       ad_bio_model=b.get('model', b['kind']))
    if x is not None and 'ad_bio_fusion' in reg.adni:
        r = predict_image_bundle(reg, 'ad_bio_fusion', x, fields)
        out.update(p_ad_bio_fusion=r['p'], pred_ad_bio_fusion=r['pred'], thr_ad_bio_fusion=r['thr'])
    for k, v in list(out.items()):
        if isinstance(v, float) and not math.isnan(v):
            out[k] = round(v, 6)
    return out
