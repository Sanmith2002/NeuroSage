"""MNI template as the "scan" through steps 3–10 with the template mask instead of HD-BET (spec §10)."""
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

ants = pytest.importorskip('ants')
pytest.importorskip('nilearn')

from app.mri import preprocess as pp  # noqa: E402
from app.schemas import MriFields  # noqa: E402

CACHE = Path(__file__).resolve().parent.parent / '.cache'


def test_crop_box_matches_training():
    import nibabel as nib
    _, m = pp.template_paths(CACHE)
    lo, hi = pp.crop_box(np.asarray(nib.load(str(m)).dataobj))
    assert lo.tolist() == [18, 21, 0] and hi.tolist() == [178, 213, 160]


def test_template_through_pipeline():
    t, _ = pp.template_paths(CACHE)
    work = Path(tempfile.mkdtemp())
    stages = []
    try:
        out = pp.run(t, work, CACHE, lambda s, p: stages.append(s), skip_skullstrip=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    assert out.x.shape == (80, 96, 80) and out.x.dtype == np.float32
    assert np.isfinite(out.x).all()
    assert out.qc['dice_mni'] >= 0.99, out.qc
    assert stages[:2] == ['convert', 'skullstrip'] and 'register' in stages


def test_normalise_float16_roundtrip():
    rng = np.random.default_rng(0)
    v = rng.normal(100, 20, (160, 192, 160)).astype(np.float32)
    m = np.zeros(v.shape, bool)
    m[20:140, 20:170, 20:140] = True
    x = pp.normalise(v, m)
    assert x.shape == (80, 96, 80)
    assert np.array_equal(x, x.astype(np.float16).astype(np.float32))
    assert np.abs(x).max() <= 5


def test_cached_nets_match_predict_adni(registry):
    """predict_adni (rebuilds nets per call) stays the reference for the cached-net path."""
    if 'ad_clin' not in registry.adni:
        pytest.skip('ADNI bundles not loaded')
    from app.mri.predict import predict_all, tabular_vector
    rng = np.random.default_rng(1)
    x = np.clip(rng.normal(0, 1, (80, 96, 80)), -5, 5).astype(np.float16).astype(np.float32)
    fields = MriFields(age_at_scan=74, sex='female', education_years=16, apoe_e4_count=1)
    ours = predict_all(registry, x, fields)
    for key, pk in [('ad_clin', 'p_ad_clin'), ('ad_bio', 'p_ad_bio')]:
        b = registry.adni[key]
        ref, _ = registry.model_defs.predict_adni(b, x, tabular_vector(b, fields)[0], device='cpu')
        assert ours[pk] == pytest.approx(float(ref[0]), abs=1e-5)
    assert abs(sum(ours['attention'].values()) - 1) < 1e-3


def test_gradcam_shape(registry):
    if 'ad_clin' not in registry.adni:
        pytest.skip('ADNI bundles not loaded')
    from app.mri.predict import gradcam
    x = np.random.default_rng(2).normal(0, 1, (80, 96, 80)).astype(np.float32)
    cam = gradcam(registry, x, MriFields(age_at_scan=70))
    assert cam.shape == (80, 96, 80) and cam.min() >= 0 and cam.max() <= 1
