"""Single source of truth for the live form (GET /v1/form-spec) and feature display names."""
from __future__ import annotations

from .features import LAST_VARS, SYMPTOM_VARS, TREND_VARS

TRI = [{'value': True, 'label': 'Yes'}, {'value': False, 'label': 'No'}, {'value': None, 'label': 'Unknown'}]
VASC = [{'value': 'absent', 'label': 'Absent'}, {'value': 'active', 'label': 'Active'},
        {'value': 'remote', 'label': 'Remote / inactive'}, {'value': None, 'label': 'Unknown'}]


def _f(key, label, type_, *, unit=None, min=None, max=None, step=None, options=None, help=None, high_impact=False,
       required=False):
    return {k: v for k, v in dict(key=key, label=label, type=type_, unit=unit, min=min, max=max, step=step,
                                  options=options, help=help, high_impact=high_impact, required=required).items()
            if v is not None}


PATIENT_FIELDS = [
    _f('id', 'Patient reference', 'text', help='A pseudonymous reference. Do not enter names or record numbers.'),
    _f('sex', 'Sex', 'select', options=[{'value': 'female', 'label': 'Female'}, {'value': 'male', 'label': 'Male'},
                                        {'value': None, 'label': 'Unknown'}]),
    _f('education_years', 'Education', 'number', unit='years', min=0, max=36, step=1),
    _f('hispanic', 'Hispanic / Latino', 'tri', options=TRI),
    _f('race', 'Race', 'select', options=[{'value': v, 'label': v.capitalize()} for v in ['white', 'black', 'asian', 'other']]
       + [{'value': None, 'label': 'Unknown'}]),
    _f('apoe_e4_count', 'APOE ε4 alleles', 'select', high_impact=True,
       options=[{'value': 0, 'label': '0 (no ε4)'}, {'value': 1, 'label': '1 (heterozygous)'},
                {'value': 2, 'label': '2 (homozygous)'}, {'value': None, 'label': 'Unknown'}]),
    _f('family_history', 'Family history of cognitive impairment', 'tri', options=TRI),
]

SYMPTOM_FIELDS = [
    _f('visual_hallucinations', 'Visual hallucinations', 'tri', options=TRI, high_impact=True, help='Clinician-judged (NACC BEVHALL)'),
    _f('rem_sleep_behaviour', 'REM sleep behaviour disorder', 'tri', options=TRI, high_impact=True, help='NACC BEREM'),
    _f('cognitive_fluctuations', 'Cognitive fluctuations', 'tri', options=TRI, help='NACC COGFLUC'),
    _f('bradykinesia', 'Bradykinesia / slowness', 'tri', options=TRI, help='NACC MOSLOW'),
    _f('tremor', 'Tremor', 'tri', options=TRI, help='NACC MOTREM'),
    _f('gait_disorder', 'Gait disorder', 'tri', options=TRI, help='NACC MOGAIT'),
    _f('falls', 'Falls', 'tri', options=TRI, help='NACC MOFALLS'),
    _f('parkinsonian_signs', 'Parkinsonian signs on exam', 'tri', options=TRI, help='NACC PARKSIGN'),
    _f('npi_hallucinations', 'Hallucinations (NPI-Q)', 'tri', options=TRI, high_impact=True, help='NACC HALL'),
    _f('npi_night_behaviour', 'Night-time behaviours (NPI-Q)', 'tri', options=TRI, help='NACC NITE'),
    _f('npi_delusions', 'Delusions (NPI-Q)', 'tri', options=TRI, help='NACC DEL'),
]

VASCULAR_FIELDS = [
    _f('hypertension', 'Hypertension', 'vascular', options=VASC),
    _f('hypercholesterolaemia', 'Hypercholesterolaemia', 'vascular', options=VASC),
    _f('diabetes', 'Diabetes', 'vascular', options=VASC),
    _f('stroke', 'Stroke', 'vascular', options=VASC, high_impact=True),
    _f('tia', 'Transient ischaemic attack', 'vascular', options=VASC),
    _f('atrial_fibrillation', 'Atrial fibrillation', 'vascular', options=VASC),
]

VISIT_FIELDS = [
    _f('date', 'Visit date', 'date', required=True),
    _f('age', 'Age at visit', 'number', unit='years', min=18, max=115, step=0.1, required=True, high_impact=True),
    _f('mmse', 'MMSE', 'number', unit='/30', min=0, max=30, step=1, high_impact=True,
       help='Enter MMSE or MoCA (not both needed). MoCA is converted with the Monsell 2016 crosswalk.'),
    _f('moca', 'MoCA', 'number', unit='/30', min=0, max=30, step=1, high_impact=True,
       help='NACC MoCA total INCLUDING the +1 education point.'),
    _f('cognition_untestable', 'Cognition untestable', 'bool', help='Disables MMSE and MoCA for this visit.'),
    _f('cdr_global', 'CDR global', 'select', options=[{'value': v, 'label': str(v)} for v in [0, 0.5, 1, 2, 3]]
       + [{'value': None, 'label': 'Unknown'}]),
    _f('cdr_sum', 'CDR sum of boxes', 'number', unit='0–18', min=0, max=18, step=0.5, high_impact=True),
    _f('gds', 'Geriatric Depression Scale', 'number', unit='/15', min=0, max=15, step=1),
    _f('bmi', 'BMI', 'number', unit='kg/m²', min=12, max=70, step=0.1, high_impact=True),
    _f('bp_systolic', 'Systolic blood pressure', 'number', unit='mmHg', min=60, max=260, step=1),
]

CSF_FIELDS = [
    _f('abeta42', 'CSF Aβ42', 'number', unit='pg/mL', min=0, step=0.1),
    _f('ptau181', 'CSF p-tau181', 'number', unit='pg/mL', min=0, step=0.1),
    _f('ttau', 'CSF total tau', 'number', unit='pg/mL', min=0, step=0.1),
    _f('assay', 'Assay / platform', 'text', help='CSF values are assay-specific and are not harmonised in this version.'),
]

MRI_FIELDS = [
    _f('file', 'T1 MPRAGE', 'file', help='NIfTI (.nii / .nii.gz) or a .zip of one DICOM series. Not stored.'),
    _f('age_at_scan', 'Age at scan', 'number', unit='years', min=18, max=115, step=0.1),
    _f('sex', 'Sex', 'select', options=[{'value': 'female', 'label': 'Female'}, {'value': 'male', 'label': 'Male'}]),
    _f('education_years', 'Education', 'number', unit='years', min=0, max=36, step=1),
    _f('apoe_e4_count', 'APOE ε4 alleles', 'select', options=[{'value': v, 'label': str(v)} for v in [0, 1, 2]]),
]

# ------------------------------------------------------------------ display names
BASE_NAMES = {
    'NACCAGE': 'Age', 'female': 'Female sex', 'EDUC': 'Education (years)', 'HISPANIC': 'Hispanic / Latino',
    'NACCNE4S': 'APOE ε4 alleles', 'NACCFAM': 'Family history', 'MMSE_EQ': 'MMSE (harmonised)', 'NACCMMSE': 'MMSE',
    'NACCMOCA': 'MoCA', 'CDRSUM': 'CDR sum of boxes', 'CDRGLOB': 'CDR global', 'NACCGDS': 'Depression (GDS)',
    'NACCBMI': 'BMI', 'BPSYS': 'Systolic BP',
    'BEVHALL': 'Visual hallucinations', 'BEREM': 'REM sleep behaviour disorder', 'COGFLUC': 'Cognitive fluctuations',
    'MOSLOW': 'Bradykinesia', 'MOTREM': 'Tremor', 'MOGAIT': 'Gait disorder', 'MOFALLS': 'Falls',
    'PARKSIGN': 'Parkinsonian signs', 'HALL': 'Hallucinations (NPI-Q)', 'NITE': 'Night-time behaviours (NPI-Q)',
    'DEL': 'Delusions (NPI-Q)',
    'HYPERTEN_present': 'Hypertension', 'HYPERCHO_present': 'Hypercholesterolaemia', 'DIABETES_present': 'Diabetes',
    'CBSTROKE_present': 'Stroke history', 'CBTIA_present': 'TIA history', 'CVAFIB_present': 'Atrial fibrillation',
    'race_white': 'Race: White', 'race_black': 'Race: Black', 'race_asian': 'Race: Asian', 'race_other': 'Race: other',
}


def _build_display_names() -> dict[str, str]:
    d: dict[str, str] = {}
    for x in LAST_VARS:
        d[f'last_{x}'] = BASE_NAMES[x] + (' (last visit)' if x not in {'female', 'EDUC', 'HISPANIC', 'NACCNE4S', 'NACCFAM'}
                                          and not x.startswith('race_') else '')
    for x in SYMPTOM_VARS:
        d[f'ever_{x}'] = f'{BASE_NAMES[x]} (ever)'
    for y in TREND_VARS:
        d[f'slope_{y}'] = f'{BASE_NAMES[y]} slope / year'
        d[f'delta_{y}'] = f'{BASE_NAMES[y]} change, first → last'
    d.update({
        'last_NACCAGE': 'Age at last visit',
        'lastavail_MMSE_EQ': 'Most recent MMSE (harmonised)', 'years_since_MMSE_EQ': 'Years since last cognitive test',
        'last_cog_untestable': 'Cognition untestable (last visit)', 'ever_cog_untestable': 'Cognition untestable (ever)',
        'n_visits': 'Number of visits', 'followup_years': 'Follow-up (years)', 'age_first_visit': 'Age at first visit',
        'missing_NACCGDS': 'GDS not recorded',
        'csf_abeta': 'CSF Aβ42', 'csf_ptau': 'CSF p-tau181', 'csf_ttau': 'CSF total tau',
        'csf_ptau_abeta': 'CSF p-tau / Aβ42', 'csf_ttau_abeta': 'CSF t-tau / Aβ42', 'has_csf': 'CSF available',
    })
    return d


DISPLAY_NAMES = _build_display_names()


def display_name(feature: str) -> str:
    return DISPLAY_NAMES.get(feature, feature)


def form_spec() -> dict:
    return {
        'patient': PATIENT_FIELDS,
        'visit': VISIT_FIELDS,
        'symptoms': SYMPTOM_FIELDS,
        'vascular': VASCULAR_FIELDS,
        'csf': CSF_FIELDS,
        'mri': MRI_FIELDS,
        'high_impact': ['apoe_e4_count', 'mmse', 'moca', 'cdr_sum', 'visual_hallucinations', 'npi_hallucinations',
                        'rem_sleep_behaviour', 'age', 'stroke', 'bmi'],
        'hints': {
            'visits': 'At least 1 visit. ≥ 3 visits over ≥ 1 year enables trend (slope) features.',
            'missing': 'Leave unknown values empty: the model imputes them, and the data-sufficiency score drops.',
        },
        'display_names': DISPLAY_NAMES,
    }
