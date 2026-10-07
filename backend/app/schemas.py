"""Request / response models. Ranges come from the training codebook (spec §5.4)."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Tri = bool | None
VascStatus = Literal['absent', 'active', 'remote'] | None

SYMPTOM_KEYS = ['visual_hallucinations', 'rem_sleep_behaviour', 'cognitive_fluctuations', 'bradykinesia', 'tremor',
                'gait_disorder', 'falls', 'parkinsonian_signs', 'npi_hallucinations', 'npi_night_behaviour', 'npi_delusions']
CDR_GLOBAL_VALUES = (0, 0.5, 1, 2, 3)
VASCULAR_KEYS = ['hypertension', 'hypercholesterolaemia', 'diabetes', 'stroke', 'tia', 'atrial_fibrillation']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Patient(Strict):
    id: str = Field('anonymous', max_length=64)
    sex: Literal['male', 'female'] | None = None
    education_years: float | None = Field(None, ge=0, le=36)
    hispanic: Tri = None
    race: Literal['white', 'black', 'asian', 'other'] | None = None
    apoe_e4_count: int | None = Field(None, ge=0, le=2)
    family_history: Tri = None


class Symptoms(Strict):
    visual_hallucinations: Tri = None
    rem_sleep_behaviour: Tri = None
    cognitive_fluctuations: Tri = None
    bradykinesia: Tri = None
    tremor: Tri = None
    gait_disorder: Tri = None
    falls: Tri = None
    parkinsonian_signs: Tri = None
    npi_hallucinations: Tri = None
    npi_night_behaviour: Tri = None
    npi_delusions: Tri = None


class Vascular(Strict):
    hypertension: VascStatus = None
    hypercholesterolaemia: VascStatus = None
    diabetes: VascStatus = None
    stroke: VascStatus = None
    tia: VascStatus = None
    atrial_fibrillation: VascStatus = None


class Visit(Strict):
    date: dt.date
    age: float = Field(..., ge=18, le=115)
    mmse: float | None = Field(None, ge=0, le=30)
    moca: float | None = Field(None, ge=0, le=30)
    cognition_untestable: bool = False
    cdr_global: float | None = None
    cdr_sum: float | None = Field(None, ge=0, le=18)
    gds: float | None = Field(None, ge=0, le=15)
    bmi: float | None = Field(None, ge=12, le=70)
    bp_systolic: float | None = Field(None, ge=60, le=260)
    symptoms: Symptoms = Field(default_factory=Symptoms)
    vascular: Vascular = Field(default_factory=Vascular)

    @field_validator('cdr_global')
    @classmethod
    def _cdr(cls, v: float | None) -> float | None:
        if v is not None and v not in CDR_GLOBAL_VALUES:
            raise ValueError('cdr_global must be one of 0, 0.5, 1, 2, 3')
        return v

    @model_validator(mode='after')
    def _untestable(self) -> 'Visit':
        if self.cognition_untestable and (self.mmse is not None or self.moca is not None):
            raise ValueError('cognition_untestable=true requires mmse and moca to be null')
        return self


class Csf(Strict):
    abeta42: float | None = None
    ptau181: float | None = None
    ttau: float | None = None
    assay: str | None = Field(None, max_length=64)


class Options(Strict):
    explain: bool = True
    model: Literal['auto', 'rf', 'xgb'] = 'auto'


class ClinicalRequest(Strict):
    patient: Patient = Field(default_factory=Patient)
    visits: list[Visit] = Field(..., min_length=1, max_length=60)
    csf: Csf | None = None
    options: Options = Field(default_factory=Options)

    @field_validator('visits')
    @classmethod
    def _unique_sorted(cls, v: list[Visit]) -> list[Visit]:
        dates = [x.date for x in v]
        if len(set(dates)) != len(dates):
            raise ValueError('visit dates must be unique')
        return sorted(v, key=lambda x: x.date)


# ---------------------------------------------------------------- MRI
class MriFields(Strict):
    age_at_scan: float | None = Field(None, ge=18, le=115)
    sex: Literal['male', 'female'] | None = None
    education_years: float | None = Field(None, ge=0, le=36)
    apoe_e4_count: int | None = Field(None, ge=0, le=2)


class MriQC(BaseModel):
    brain_cm3: float | None = None
    dice_mni: float | None = None
    registration: str | None = None
    passed: bool


class MriResult(BaseModel):
    p_ad_clin: float | None = None
    pred_ad_clin: int | None = None
    thr_ad_clin: float | None = None
    fold_sd_ad_clin: float | None = None
    ad_clin_model: str | None = None
    p_ad_bio: float | None = None
    pred_ad_bio: int | None = None
    thr_ad_bio: float | None = None
    ad_bio_model: str | None = None
    p_ad_bio_fusion: float | None = None
    pred_ad_bio_fusion: int | None = None
    thr_ad_bio_fusion: float | None = None
    attention: dict[str, float] | None = None
    qc: MriQC | None = None
    gradcam_png: str | None = None
    qc_png: str | None = None
    timings_s: dict[str, float] = Field(default_factory=dict)
    source: Literal['upload', 'demo'] = 'upload'


class AssessRequest(Strict):
    clinical: ClinicalRequest
    mri_result: MriResult | None = None


# ---------------------------------------------------------------- generic
class Health(BaseModel):
    status: str
    models_loaded: dict[str, Any]
    version: str
