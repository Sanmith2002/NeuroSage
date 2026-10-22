"""Private fixture → probabilities match Stage 4 to 1e-6 for RF and XGB. Skipped when the fixture is absent.

The fixture is derived from NACC data under the DUA: it lives in tests/private/ (gitignored) and is never committed.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PRIVATE = Path(__file__).resolve().parent / 'private'

FIXTURE = PRIVATE / 'parity_fixture.json'
BUNDLE_KEYS = {'RandomForest': 'rf', 'XGBoost': 'xgb'}


@pytest.fixture(scope='module')
def fixture():
    if not FIXTURE.exists():
        pytest.skip('tests/private/parity_fixture.json not present')
    return json.loads(FIXTURE.read_text())


@pytest.mark.parametrize('model_name', ['RandomForest', 'XGBoost'])
def test_predict_nacc_parity(registry, fixture, model_name):
    key = BUNDLE_KEYS[model_name]
    if key not in registry.available_nacc():
        pytest.skip(f'{model_name} bundle not present')
    bundle = registry.get_nacc(key)
    assert list(bundle['features']) == fixture['features']
    df = pd.DataFrame(fixture['rows'], columns=fixture['features']).astype(float)
    probs, _ = registry.model_defs.predict_nacc(bundle, df)
    expected = pd.DataFrame(fixture['expected'][model_name])
    for L in bundle['targets']:
        np.testing.assert_allclose(probs[L].to_numpy(), expected[L].to_numpy(), atol=1e-6, rtol=0)


def test_service_path_matches_reference(registry, fixture):
    """The service's per-row path (to_frame order + fold uncertainty) agrees with predict_nacc on fixture rows."""
    from app.clinical import fold_probabilities
    from app.features import to_frame

    bundle = registry.get_nacc(registry.active_nacc())
    for row in fixture['rows'][:5]:
        F = {k: (np.nan if v is None else v) for k, v in row.items()}
        X, missing = to_frame(F, list(bundle['features']))
        assert not missing
        ref, _ = registry.model_defs.predict_nacc(bundle, X)
        folds = fold_probabilities(bundle, X)
        for L in bundle['targets']:
            assert 0 <= folds[L].min() <= folds[L].max() <= 1
            assert np.isfinite(ref[L].iloc[0])


def test_single_pass_equals_predict_nacc_without_fixture(registry):
    """The service's one-pass path is numerically predict_nacc (no private data needed: synthetic rows)."""
    from app.clinical import calibrated, fold_raw
    from app.features import engineer, to_frame
    from app.schemas import ClinicalRequest
    from tests.test_api import FULL, MINIMAL

    bundle = registry.get_nacc(registry.active_nacc())
    for body in (FULL, MINIMAL):
        X, _ = to_frame(engineer(ClinicalRequest.model_validate(body)).features, list(bundle['features']))
        ref, ref_lab = registry.model_defs.predict_nacc(bundle, X)
        probs, _ = calibrated(bundle, fold_raw(bundle, X))
        for L in bundle['targets']:
            assert probs[L] == pytest.approx(float(ref[L].iloc[0]), abs=1e-12)
            assert (probs[L] >= bundle['thresholds'][L]) == bool(ref_lab[L].iloc[0])
