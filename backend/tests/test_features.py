"""Hand-built visit histories → expected features (spec §10, test_features cases a–h)."""
import datetime as dt
import math

import numpy as np
import pytest

from app.features import MOCA_TO_MMSE, engineer, to_frame
from app.schemas import ClinicalRequest


def req(visits, patient=None, csf=None):
    return ClinicalRequest.model_validate({'patient': patient or {}, 'visits': visits, 'csf': csf})


def v(date, age, **kw):
    return {'date': date, 'age': age, **kw}


def nan(x):
    return isinstance(x, float) and math.isnan(x)


def test_a_single_visit():
    F = engineer(req([v('2023-01-01', 70, mmse=25, cdr_sum=1, gds=2)])).features
    assert F['n_visits'] == 1 and F['followup_years'] == 0
    assert all(nan(F[f'slope_{y}']) for y in ['MMSE_EQ', 'CDRSUM', 'NACCGDS'])
    assert F['delta_MMSE_EQ'] == 0 and F['age_first_visit'] == 70


def test_b_three_visits_two_years_slope_equals_polyfit():
    visits = [v('2020-01-01', 70, mmse=28), v('2021-01-01', 71, mmse=26), v('2022-01-01', 72, mmse=21)]
    F = engineer(req(visits)).features
    t = np.array([0, 366, 731]) / 365.25
    assert F['slope_MMSE_EQ'] == pytest.approx(np.polyfit(t, [28, 26, 21], 1)[0], abs=1e-12)
    assert F['delta_MMSE_EQ'] == -7
    assert F['followup_years'] == pytest.approx(731 / 365.25)


def test_c_three_visits_half_year_slope_nan():
    visits = [v('2020-01-01', 70, mmse=28), v('2020-04-01', 70.2, mmse=26), v('2020-07-01', 70.5, mmse=25)]
    assert nan(engineer(req(visits)).features['slope_MMSE_EQ'])


def test_d_moca_crosswalk():
    eng = engineer(req([v('2023-01-01', 74, moca=21)]))
    assert eng.features['last_MMSE_EQ'] == 27 == MOCA_TO_MMSE[21]
    assert nan(eng.features['last_NACCMMSE']) and eng.features['last_NACCMOCA'] == 21
    assert eng.harmonisation_log[0]['standard'] == 'MMSE_EQ 27'


def test_e_last_visit_untestable():
    visits = [v('2020-01-01', 70, mmse=24), v('2021-07-02', 71.5, mmse=20), v('2022-07-02', 72.5, cognition_untestable=True)]
    F = engineer(req(visits)).features
    assert nan(F['last_MMSE_EQ'])
    assert F['lastavail_MMSE_EQ'] == 20
    assert F['years_since_MMSE_EQ'] == pytest.approx(365 / 365.25)
    assert F['last_cog_untestable'] == 1.0 and F['ever_cog_untestable'] == 1.0


def test_untestable_with_score_rejected():
    with pytest.raises(ValueError):
        req([v('2020-01-01', 70, mmse=24, cognition_untestable=True)])


def test_f_vascular_remote_is_present():
    F = engineer(req([v('2023-01-01', 70, vascular={'stroke': 'remote', 'hypertension': 'absent'})])).features
    assert F['last_CBSTROKE_present'] == 1.0 and F['last_HYPERTEN_present'] == 0.0
    assert nan(F['last_DIABETES_present'])


def test_g_race_null_all_nan():
    F = engineer(req([v('2023-01-01', 70)])).features
    assert all(nan(F[f'last_race_{r}']) for r in ['white', 'black', 'asian', 'other'])
    F = engineer(req([v('2023-01-01', 70)], patient={'race': 'asian'})).features
    assert [F[f'last_race_{r}'] for r in ['white', 'black', 'asian', 'other']] == [0, 0, 1, 0]


def test_last_row_not_carried_forward_and_ever():
    visits = [v('2020-01-01', 70, gds=3, symptoms={'rem_sleep_behaviour': True}),
              v('2021-01-01', 71, symptoms={'rem_sleep_behaviour': None})]
    F = engineer(req(visits)).features
    assert nan(F['last_NACCGDS']) and F['missing_NACCGDS'] == 1.0
    assert nan(F['last_BEREM']) and F['ever_BEREM'] == 1.0
    assert nan(F['ever_BEVHALL'])


def test_csf_ratios_and_flags():
    eng = engineer(req([v('2023-01-01', 70)], csf={'abeta42': 500, 'ptau181': 50, 'ttau': 0}))
    F = eng.features
    assert F['csf_ptau_abeta'] == pytest.approx(0.1) and nan(F['csf_ttau']) and nan(F['csf_ttau_abeta'])
    assert F['has_csf'] == 1.0
    assert any('not harmonised' in w for w in eng.warnings)
    assert engineer(req([v('2023-01-01', 70)])).features['has_csf'] == 0.0


def test_visits_sorted_and_unique():
    eng = engineer(req([v('2021-01-01', 71, mmse=20), v('2020-01-01', 70, mmse=25)]))
    assert eng.features['last_MMSE_EQ'] == 20 and eng.features['age_first_visit'] == 70
    with pytest.raises(ValueError):
        req([v('2020-01-01', 70), v('2020-01-01', 71)])


def test_sixty_six_features():
    F = engineer(req([v('2023-01-01', 70)])).features
    assert len(F) == 66


def test_h_order_matches_bundle(registry):
    bundle = registry.get_nacc(registry.active_nacc())
    F = engineer(req([v(dt.date(2023, 1, 1), 70)])).features
    X, missing = to_frame(F, list(bundle['features']))
    assert list(X.columns) == list(bundle['features'])
    assert missing == [], f'engineering does not produce: {missing}'
    assert set(F) == set(bundle['features'])
