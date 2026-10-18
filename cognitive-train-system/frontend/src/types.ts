export type Diagnosis = 'AD' | 'LBD' | 'PD' | 'VD' | 'MX'

export interface DiagnosisProbabilities {
  AD: number
  LBD: number
  PD: number
  VD: number
}

export interface NsProfile {
  name: string
  age: number
  sex: 'M' | 'F'
  education: number
  language: 'EN' | 'SI'
  diagnosis: Diagnosis
  probabilities: DiagnosisProbabilities
}

export const DIAGNOSIS_PRESETS: Record<
  Diagnosis,
  { label: string; probabilities: DiagnosisProbabilities }
> = {
  AD:  { label: "Alzheimer's Disease",      probabilities: { AD: 0.85, LBD: 0.05, PD: 0.05, VD: 0.05 } },
  LBD: { label: 'Lewy Body Dementia',       probabilities: { AD: 0.05, LBD: 0.85, PD: 0.05, VD: 0.05 } },
  PD:  { label: "Parkinson's Disease Dementia", probabilities: { AD: 0.05, LBD: 0.10, PD: 0.75, VD: 0.10 } },
  VD:  { label: 'Vascular Dementia',        probabilities: { AD: 0.10, LBD: 0.05, PD: 0.05, VD: 0.80 } },
  MX:  { label: 'Mixed / Unclear',          probabilities: { AD: 0.25, LBD: 0.25, PD: 0.25, VD: 0.25 } },
}

export const NS_PROFILE_KEY = 'ns_profile'
