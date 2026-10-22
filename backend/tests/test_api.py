"""Contract tests for the HTTP API (spec §10)."""
import pytest

MINIMAL = {'visits': [{'date': '2024-05-01', 'age': 76}]}
FULL = {
    'patient': {'id': 'P-TEST-001', 'sex': 'female', 'education_years': 14, 'hispanic': False, 'race': 'asian',
                'apoe_e4_count': 1, 'family_history': True},
    'visits': [
        {'date': '2021-03-14', 'age': 72.2, 'moca': 24, 'cdr_global': 0.5, 'cdr_sum': 1.5, 'gds': 3, 'bmi': 24.1,
         'bp_systolic': 138, 'symptoms': {'rem_sleep_behaviour': True},
         'vascular': {'hypertension': 'active', 'stroke': 'absent'}},
        {'date': '2022-03-20', 'age': 73.2, 'mmse': 25, 'cdr_global': 0.5, 'cdr_sum': 2.5, 'gds': 4, 'bmi': 23.8,
         'bp_systolic': 140},
        {'date': '2023-03-14', 'age': 74.2, 'moca': 21, 'cdr_global': 0.5, 'cdr_sum': 3.0, 'gds': 4, 'bmi': 24.1,
         'bp_systolic': 138, 'symptoms': {'visual_hallucinations': False, 'rem_sleep_behaviour': True},
         'vascular': {'hypertension': 'active', 'hypercholesterolaemia': 'remote', 'stroke': 'absent'}},
    ],
    'csf': {'abeta42': 600, 'ptau181': 60, 'ttau': 400, 'assay': 'Elecsys'},
    'options': {'explain': True, 'model': 'auto'},
}
SIGNALS = {'dataSufficiency', 'distributionConformity', 'predictionCertainty', 'modalityAgreement',
           'domainFamiliarity', 'explanationReliability', 'clinicalHarmRisk'}


def check_document(doc):
    assert doc['schema'] == 'neurosage.multilabel/v1'
    assert doc['disclaimer'] == 'Research prototype — not for clinical use.'
    assert doc['component']['id'] == 'ad-copathology' and doc['component']['owner'] == 'IT23174276'
    nacc = [l for l in doc['labels'] if l['source'] == 'clinical']
    assert [l['key'] for l in nacc] == ['y_AD', 'y_LBD', 'y_VD']
    for l in nacc:
        assert 0 <= l['probability'] <= 1 and 0 < l['threshold'] < 1
        assert l['predicted'] == (l['probability'] >= l['threshold'])
        assert l['uncertainty']['fold_sd'] >= 0
    assert set(doc['reliability_signals']) == SIGNALS
    assert doc['reliability_signals']['clinicalHarmRisk'] is None
    for s in doc['reliability_signals'].values():
        if s is not None:
            assert 0 <= s['score'] <= 1
    assert {m['name'] for m in doc['modalities']} == {'Clinical data', 'Genetic data', 'Biomarkers', 'MRI'}


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200 and r.json()['status'] == 'ok'


def test_models_and_form_spec(client):
    m = client.get('/v1/models').json()
    assert m['active_nacc_model'] in {'rf', 'xgb'} and m['preprocessing']['crop']['lo'] == [18, 21, 0]
    fs = client.get('/v1/form-spec').json()
    assert {f['key'] for f in fs['visit']} >= {'date', 'age', 'mmse', 'moca', 'cdr_sum'}


@pytest.mark.parametrize('bad', [
    {'visits': [{'date': '2024-05-01', 'age': 12}]},
    {'visits': [{'date': '2024-05-01', 'age': 70, 'mmse': 31}]},
    {'visits': [{'date': '2024-05-01', 'age': 70, 'cdr_global': 0.7}]},
    {'visits': [{'date': '2024-05-01', 'age': 70, 'bmi': 90}]},
    {'visits': [{'date': '2024-05-01', 'age': 70}], 'patient': {'education_years': 40}},
    {'visits': []},
    {'visits': [{'date': '2024-05-01', 'age': 70}, {'date': '2024-05-01', 'age': 71}]},
])
def test_422_on_invalid(client, bad):
    assert client.post('/v1/clinical/predict', json=bad).status_code == 422


def test_minimal_request(client):
    r = client.post('/v1/clinical/predict', json=MINIMAL)
    assert r.status_code == 200, r.text
    doc = r.json()
    check_document(doc)
    assert doc['reliability_signals']['dataSufficiency']['score'] == pytest.approx(1 / 8)
    assert doc['reliability_signals']['modalityAgreement'] is None


def test_full_request_with_shap(client):
    r = client.post('/v1/clinical/predict', json=FULL)
    assert r.status_code == 200, r.text
    doc = r.json()
    check_document(doc)
    ad = doc['labels'][0]
    assert ad['explanation']['method'] == 'shap' and len(ad['explanation']['top']) == 8
    assert ad['explanation']['scale'] in {'probability', 'log-odds'}
    assert {t['direction'] for t in ad['explanation']['top']} <= {'supports', 'reduces'}
    assert any(h['standard'] == 'MMSE_EQ 27' for h in doc['harmonisation_log'])
    assert doc['derived_features']['n_visits'] == 3 and doc['derived_features']['slope_MMSE_EQ'] is not None


def test_explain_false_has_no_explanation(client):
    doc = client.post('/v1/clinical/predict', json={**MINIMAL, 'options': {'explain': False}}).json()
    assert all('explanation' not in l for l in doc['labels'])


def test_features_endpoint(client):
    r = client.post('/v1/clinical/features', json=FULL).json()
    assert len(r['features']) == 66 and r['not_produced'] == []


def test_assess_merges_mri(client):
    mri = {'p_ad_clin': 0.9, 'pred_ad_clin': 1, 'thr_ad_clin': 0.45, 'p_ad_bio': 0.6, 'pred_ad_bio': 1,
           'thr_ad_bio': 0.5, 'attention': {'mri': 0.7, 'tabular': 0.3},
           'qc': {'brain_cm3': 1180, 'dice_mni': 0.96, 'registration': 'AffineFast', 'passed': True}}
    doc = client.post('/v1/assess', json={'clinical': {**FULL, 'options': {'explain': False}}, 'mri_result': mri}).json()
    check_document(doc)
    keys = [l['key'] for l in doc['labels']]
    assert 'ad_clin_mri' in keys and 'ad_bio' in keys
    assert doc['reliability_signals']['modalityAgreement'] is not None
    assert next(m for m in doc['modalities'] if m['name'] == 'MRI')['status'] == 'AVAILABLE'


def test_api_key(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), 'api_key', 'secret')
    assert client.post('/v1/clinical/predict', json=MINIMAL).status_code == 401
    assert client.post('/v1/clinical/predict', json=MINIMAL, headers={'X-API-Key': 'secret'}).status_code == 200


def test_mri_job_rejects_bad_upload(client):
    if 'ad_clin' not in client.app.state.registry.adni:
        pytest.skip('ADNI bundles not loaded')
    r = client.post('/v1/mri/jobs', files={'file': ('scan.txt', b'not a scan')})
    assert r.status_code == 422
    assert client.get('/v1/mri/jobs/does-not-exist').status_code == 404


def test_mri_job_runs_in_background(client, monkeypatch):
    """The upload returns at once with a job id; polling reaches the same MriResult the SSE stream sends."""
    import time
    import numpy as np
    from app.mri import preprocess
    if 'ad_clin' not in client.app.state.registry.adni:
        pytest.skip('ADNI bundles not loaded')

    def fake_run(src, work, cache_dir, progress, device='cpu'):
        progress('skullstrip', 0.10)
        x = np.random.default_rng(3).normal(0, 1, (80, 96, 80)).astype(np.float16).astype(np.float32)
        return preprocess.Preprocessed(x, {'brain_cm3': 1200.0, 'dice_mni': 0.95, 'registration': 'AffineFast',
                                           'passed': True}, {'convert': 0.1})

    monkeypatch.setattr(preprocess, 'run', fake_run)
    r = client.post('/v1/mri/jobs', files={'file': ('scan.nii.gz', b'\x1f\x8b')}, data={'fields': '{"age_at_scan": 74}'})
    assert r.status_code == 202, r.text
    job = r.json()
    for _ in range(300):
        if job['status'] in ('done', 'error'):
            break
        time.sleep(0.1)
        job = client.get(f'/v1/mri/jobs/{job["job_id"]}').json()
    assert job['status'] == 'done', job
    res = job['result']
    assert 0 <= res['p_ad_clin'] <= 1 and res['qc']['passed'] and res['source'] == 'upload'
    assert client.get(res['qc_png']).status_code == 200
