// Shared NeuroSage view types. Every case shown in the app comes from the trained models served by the
// AD co-pathology service (lib/ad/*); there is no static or mock patient data.

export type CaseId = string;
export type SafetyStatus = 'TRUST' | 'CAUTION' | 'DEFER';
export type SignalLevel = 'HIGH' | 'MEDIUM' | 'LOW';
export type ModalityStatus = 'AVAILABLE' | 'MISSING' | 'PARTIAL' | 'NOT_APPLICABLE';
export type AssessmentStage = 'patient' | 'harmonization' | 'predictions' | 'safety' | 'report';

export interface Modality {
  name: string;
  status: ModalityStatus;
  summary: string;
  details: string[];
}

export interface Prediction {
  label: string;
  probability: number;
  safetyStatus: SafetyStatus;
}

export interface SafetySignal {
  key:
    | 'dataSufficiency'
    | 'distributionConformity'
    | 'predictionCertainty'
    | 'modalityAgreement'
    | 'domainFamiliarity'
    | 'explanationReliability'
    | 'clinicalHarmRisk';
  label: string;
  score: number;
  level: SignalLevel;
  description: string;
}

/** What the shell, stepper and dashboard need to know about one assessed patient. */
export interface CaseView {
  id: CaseId;
  createdAt: string;
  shortLabel: string;
  title: string;
  note: string;
  dataStatus: string;
  patient: {
    id: string;
    age: number;
    sex: string;
    educationYears: number;
    cohort: string;
  };
  modalities: Modality[];
  adPredictions: Prediction[];
  safety: {
    overallStatus: SafetyStatus;
    reliabilityScore: number;
    signals: SafetySignal[];
  };
}

export const assessmentStages: Array<{
  key: AssessmentStage;
  label: string;
  shortLabel: string;
}> = [
  { key: 'patient', label: 'Patient data', shortLabel: 'Data' },
  { key: 'harmonization', label: 'Harmonization', shortLabel: 'Harmonize' },
  { key: 'predictions', label: 'AI predictions', shortLabel: 'Predict' },
  { key: 'safety', label: 'Safety gate', shortLabel: 'Safety' },
  { key: 'report', label: 'Clinical report', shortLabel: 'Report' },
];

export function isAssessmentStage(value: string): value is AssessmentStage {
  return assessmentStages.some((stage) => stage.key === value);
}

export function caseHref(caseId: CaseId, stage: AssessmentStage): string {
  return `/assessment/${caseId}/${stage}`;
}
