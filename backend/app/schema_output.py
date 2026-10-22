"""Builds the shared `neurosage.multilabel/v1` document (spec §7) consumed by the Safety and Report components."""
from __future__ import annotations

import datetime as dt

from .clinical import MODEL_IDS, ClinicalResult, _num
from .config import VERSION
from .features import Engineered
from .registry import Registry
from .schemas import ClinicalRequest, MriResult

SCHEMA = 'neurosage.multilabel/v1'
DISCLAIMER = 'Research prototype — not for clinical use.'
OPENSET_WARNING = 'Open-set detection is experimental (validation AUROC ≈ 0.5); it cannot rule out other diseases.'
TARGET_WARNING = ('The clinical model estimates autopsy neuropathology in NACC participants who came to autopsy; '
                  'it is not a diagnosis and may not transfer to living memory-clinic populations.')
DERIVED = ['n_visits', 'followup_years', 'age_first_visit', 'lastavail_MMSE_EQ', 'years_since_MMSE_EQ',
           'slope_MMSE_EQ', 'slope_CDRSUM', 'slope_NACCGDS', 'delta_MMSE_EQ', 'delta_CDRSUM', 'delta_NACCGDS',
           'csf_ptau_abeta', 'csf_ttau_abeta']


def _modalities(req: ClinicalRequest, F: dict, mri: MriResult | None) -> list[dict]:
    n, fu = int(F['n_visits']), F['followup_years']
    mods = [{'name': 'Clinical data', 'status': 'AVAILABLE',
             'detail': f'{n} visit{"s" if n != 1 else ""}, {fu:.1f} y follow-up'}]
    e4 = req.patient.apoe_e4_count
    mods.append({'name': 'Genetic data', 'status': 'MISSING' if e4 is None else 'AVAILABLE',
                 'detail': 'APOE not entered' if e4 is None else f'APOE ε4 × {e4}'})
    csf = req.csf
    vals = [] if csf is None else [v for v in (csf.abeta42, csf.ptau181, csf.ttau) if v is not None and v > 0]
    if not vals:
        mods.append({'name': 'Biomarkers', 'status': 'MISSING', 'detail': 'No CSF entered'})
    else:
        assay = f' ({csf.assay})' if csf.assay else ''
        mods.append({'name': 'Biomarkers', 'status': 'AVAILABLE' if len(vals) == 3 else 'PARTIAL',
                     'detail': f'CSF {len(vals)}/3 analytes{assay}; not harmonised across assays'})
    if mri is None or mri.p_ad_clin is None:
        mods.append({'name': 'MRI', 'status': 'MISSING', 'detail': 'No T1 MRI analysed'})
    else:
        dice = mri.qc.dice_mni if mri.qc else None
        mods.append({'name': 'MRI', 'status': 'AVAILABLE',
                     'detail': 'T1, QC passed' + (f' (Dice {dice:.3f})' if dice is not None else '')
                     + (' · demo volume' if mri.source == 'demo' else '')})
    return mods


def _mri_labels(mri: MriResult) -> list[dict]:
    out = []
    if mri.p_ad_clin is not None:
        out.append({'key': 'ad_clin_mri', 'label': 'Clinical AD (MRI + tabular)', 'probability': mri.p_ad_clin,
                    'threshold': mri.thr_ad_clin, 'predicted': bool(mri.pred_ad_clin), 'source': 'mri',
                    'uncertainty': {'fold_sd': mri.fold_sd_ad_clin} if mri.fold_sd_ad_clin is not None else None,
                    'performance': {'test_auroc': 0.953, 'test_auroc_ci': [0.909, 0.987], 'test_bacc': 0.862, 'n_test': 106},
                    'explanation': {'method': 'gradcam', 'image': mri.gradcam_png, 'attention': mri.attention,
                                    'caption': 'Model attention, not a lesion map.'}})
    if mri.p_ad_bio is not None:
        out.append({'key': 'ad_bio', 'label': 'CSF-biomarker AD (predicted)', 'probability': mri.p_ad_bio,
                    'threshold': mri.thr_ad_bio, 'predicted': bool(mri.pred_ad_bio), 'source': 'tabular',
                    'performance': {'test_auroc': 0.759, 'test_auroc_ci': [0.650, 0.850], 'test_bacc': 0.729, 'n_test': 89},
                    'note': 'Predicts CSF pTau181/Aβ42 > 0.025 from age, sex, education and APOE only (no MRI).'})
    if mri.p_ad_bio_fusion is not None:
        out.append({'key': 'ad_bio_fusion', 'label': 'CSF-biomarker AD (MRI fusion)', 'probability': mri.p_ad_bio_fusion,
                    'threshold': mri.thr_ad_bio_fusion, 'predicted': bool(mri.pred_ad_bio_fusion), 'source': 'mri',
                    'performance': {'test_auroc': 0.786, 'test_auroc_ci': [0.690, 0.872], 'test_bacc': 0.652, 'n_test': 89}})
    return out


def modality_agreement(cr: ClinicalResult, mri: MriResult | None) -> dict | None:
    if mri is None or mri.p_ad_clin is None:
        return None
    p_clin = next(l['probability'] for l in cr.labels if l['key'] == 'y_AD')
    score = 1 - abs(p_clin - mri.p_ad_clin)
    return {'score': round(score, 4), 'detail': f'clinical P(AD) {p_clin:.2f} vs MRI P(AD) {mri.p_ad_clin:.2f}',
            'note': 'Different targets: autopsy AD neuropathology (NACC) vs clinical AD diagnosis (ADNI).'}


def build_document(reg: Registry, req: ClinicalRequest, eng: Engineered, cr: ClinicalResult,
                   mri: MriResult | None = None) -> dict:
    F = cr.features
    models = {'clinical': MODEL_IDS.get(cr.model_name, cr.model_name)}
    if 'ad_clin' in reg.adni:
        models['mri'] = f"ADNI-Fusion-{reg.adni['ad_clin'].get('arch', 'unknown')}"
    if 'ad_bio' in reg.adni:
        models['ad_bio'] = 'ADNI-Tabular-LogReg'
    signals = dict(cr.signals)
    signals['modalityAgreement'] = modality_agreement(cr, mri)
    warnings = [OPENSET_WARNING, TARGET_WARNING] + cr.warnings
    if mri is not None and mri.p_ad_clin is not None:
        warnings.append('Grad-CAM shows model attention, not a lesion map.')
    return {
        'schema': SCHEMA,
        'component': {'id': 'ad-copathology', 'owner': 'IT23174276', 'version': VERSION, 'models': models},
        'patient_ref': req.patient.id,
        'generated_at': dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'modalities': _modalities(req, F, mri),
        'labels': cr.labels + (_mri_labels(mri) if mri is not None else []),
        'reliability_signals': signals,
        'warnings': warnings,
        'harmonisation_log': eng.harmonisation_log,
        'derived_features': {k: _num(F.get(k)) for k in DERIVED},
        'mri': mri.model_dump(exclude_none=True) if mri is not None else None,
        'timings_s': cr.timings_s,
        'disclaimer': DISCLAIMER,
    }
