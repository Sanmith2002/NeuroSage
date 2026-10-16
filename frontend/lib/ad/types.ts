// TypeScript mirror of the shared `neurosage.multilabel/v1` document (AD component spec §7)
// and of the AD service request bodies (spec §4.1).

export type Tri = boolean | null;
export type VascularStatus = 'absent' | 'active' | 'remote' | null;
export type ModalityStatus = 'AVAILABLE' | 'MISSING' | 'PARTIAL' | 'NOT_APPLICABLE';

export const symptomKeys = [
  'visual_hallucinations', 'rem_sleep_behaviour', 'cognitive_fluctuations', 'bradykinesia', 'tremor',
  'gait_disorder', 'falls', 'parkinsonian_signs', 'npi_hallucinations', 'npi_night_behaviour', 'npi_delusions',
] as const;
export const vascularKeys = ['hypertension', 'hypercholesterolaemia', 'diabetes', 'stroke', 'tia', 'atrial_fibrillation'] as const;

export type SymptomKey = (typeof symptomKeys)[number];
export type VascularKey = (typeof vascularKeys)[number];

export interface PatientInput {
  id: string;
  sex: 'male' | 'female' | null;
  education_years: number | null;
  hispanic: Tri;
  race: 'white' | 'black' | 'asian' | 'other' | null;
  apoe_e4_count: 0 | 1 | 2 | null;
  family_history: Tri;
}

export interface VisitInput {
  date: string;
  age: number;
  mmse: number | null;
  moca: number | null;
  cognition_untestable: boolean;
  cdr_global: number | null;
  cdr_sum: number | null;
  gds: number | null;
  bmi: number | null;
  bp_systolic: number | null;
  symptoms: Partial<Record<SymptomKey, Tri>>;
  vascular: Partial<Record<VascularKey, VascularStatus>>;
}

export interface CsfInput {
  abeta42: number | null;
  ptau181: number | null;
  ttau: number | null;
  assay: string | null;
}

export interface ClinicalRequest {
  patient: PatientInput;
  visits: VisitInput[];
  csf: CsfInput | null;
  options: { explain: boolean; model: 'auto' | 'rf' | 'xgb' };
}

export interface MriFields {
  age_at_scan: number | null;
  sex: 'male' | 'female' | null;
  education_years: number | null;
  apoe_e4_count: 0 | 1 | 2 | null;
}

export interface MriResult {
  p_ad_clin?: number;
  pred_ad_clin?: number;
  thr_ad_clin?: number;
  fold_sd_ad_clin?: number;
  ad_clin_model?: string;
  p_ad_bio?: number;
  pred_ad_bio?: number;
  thr_ad_bio?: number;
  ad_bio_model?: string;
  p_ad_bio_fusion?: number;
  pred_ad_bio_fusion?: number;
  thr_ad_bio_fusion?: number;
  attention?: { mri: number; tabular: number };
  qc?: { brain_cm3?: number; dice_mni?: number; registration?: string; passed: boolean };
  gradcam_png?: string;
  qc_png?: string;
  timings_s?: Record<string, number>;
  source?: 'upload' | 'demo';
}

export interface ShapFeature {
  feature: string;
  display_name: string;
  value: number | null;
  shap: number;
  direction: 'supports' | 'reduces';
}

export interface LabelResult {
  key: string;
  label: string;
  probability: number;
  threshold: number;
  predicted: boolean;
  source: 'clinical' | 'mri' | 'tabular';
  uncertainty?: { fold_mean?: number; fold_sd?: number; margin?: number } | null;
  calibration?: { method: string; test_ece?: number | null };
  performance?: {
    test_auroc?: number;
    test_auroc_ci?: [number, number];
    test_auprc?: number;
    test_bacc?: number;
    test_ece?: number;
    n_test?: number;
  };
  explanation?: {
    method: 'shap' | 'gradcam';
    scale?: 'probability' | 'log-odds';
    stability_spearman?: number;
    stability_jaccard_top10?: number;
    top?: ShapFeature[];
    image?: string;
    caption?: string;
    attention?: { mri: number; tabular: number } | null;
  };
  note?: string;
}

export interface ReliabilitySignal {
  score: number;
  detail: string;
  [extra: string]: unknown;
}

export type ReliabilityKey =
  | 'dataSufficiency'
  | 'distributionConformity'
  | 'predictionCertainty'
  | 'modalityAgreement'
  | 'domainFamiliarity'
  | 'explanationReliability'
  | 'clinicalHarmRisk';

export interface SharedDocument {
  schema: 'neurosage.multilabel/v1';
  component: { id: string; owner: string; version: string; models: Record<string, string> };
  patient_ref: string;
  generated_at: string;
  modalities: Array<{ name: string; status: ModalityStatus; detail: string }>;
  labels: LabelResult[];
  reliability_signals: Record<ReliabilityKey, ReliabilitySignal | null>;
  warnings: string[];
  harmonisation_log: Array<{ visit?: string; original: string; standard: string; rule: string }>;
  derived_features?: Record<string, number | null>;
  mri?: MriResult | null;
  timings_s?: Record<string, number>;
  disclaimer: string;
}

export interface FormField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'tri' | 'bool' | 'date' | 'vascular' | 'file';
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string | number | boolean | null; label: string }>;
  help?: string;
  high_impact?: boolean;
  required?: boolean;
}

export interface FormSpec {
  patient: FormField[];
  visit: FormField[];
  symptoms: FormField[];
  vascular: FormField[];
  csf: FormField[];
  mri: FormField[];
  high_impact: string[];
  hints: Record<string, string>;
  display_names: Record<string, string>;
}

export interface DemoMriCase {
  id: string;
  description: string;
  fields: Partial<MriFields>;
}

export type MriStage = 'queued' | 'upload' | 'convert' | 'skullstrip' | 'bias' | 'register' | 'normalise' | 'predict' | 'explain';

export const DISCLAIMER = 'Research prototype — not for clinical use.';
