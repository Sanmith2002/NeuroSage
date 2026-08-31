export type CaseId = 'CASE-A' | 'CASE-B' | 'CASE-C' | 'CASE-D';
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

export interface FeatureContribution {
  label: string;
  value: number;
  direction: 'supports' | 'reduces';
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

export interface DemoCase {
  id: CaseId;
  shortLabel: string;
  title: string;
  description: string;
  demoPoint: string;
  dataStatus: string;
  patient: {
    id: string;
    age: number;
    sex: string;
    educationYears: number;
    cohort: string;
  };
  modalities: Modality[];
  harmonizedFeatures: Array<{
    originalFeature: string;
    source: string;
    standardFeature: string;
    value: string;
  }>;
  adPredictions: Prediction[];
  pdPredictions: Prediction[];
  adFeatures: FeatureContribution[];
  pdFeatures: FeatureContribution[];
  safety: {
    overallStatus: SafetyStatus;
    reliabilityScore: number;
    signals: SafetySignal[];
    reasons: string[];
    recommendedAction: string;
  };
  report: {
    patientSummary: string;
    supportingEvidence: string[];
    safetyConsiderations: string[];
    recommendation: string;
    sources: Array<{
      name: string;
      status: 'Retrieved' | 'Included';
      detail: string;
    }>;
  };
}

const sources: DemoCase['report']['sources'] = [
  {
    name: 'Clinical guideline',
    status: 'Retrieved',
    detail: 'Mock neurological assessment guidance used to frame interpretation.',
  },
  {
    name: 'Research evidence',
    status: 'Retrieved',
    detail: 'Static evidence summary for multimodal neurodegenerative disease assessment.',
  },
  {
    name: 'Model explanation',
    status: 'Included',
    detail: 'Feature-level contributions from both disease-analysis components.',
  },
  {
    name: 'Patient prediction',
    status: 'Included',
    detail: 'Multi-label Alzheimer’s, co-pathology, and Parkinson’s probabilities.',
  },
  {
    name: 'Safety assessment',
    status: 'Included',
    detail: 'Reliability signals, label-level status, reasons, and recommended action.',
  },
];

function safetySignal(
  key: SafetySignal['key'],
  label: string,
  score: number,
  level: SignalLevel,
  description: string,
): SafetySignal {
  return { key, label, score, level, description };
}

const commonMapping = [
  { originalFeature: 'AGE', source: 'ADNI', standardFeature: 'Age' },
  { originalFeature: 'pt_age', source: 'PPMI', standardFeature: 'Age' },
  { originalFeature: 'MMSE_TOTAL', source: 'ADNI', standardFeature: 'MMSE' },
  { originalFeature: 'updrs_total', source: 'PPMI', standardFeature: 'UPDRS' },
  { originalFeature: 'APOE4', source: 'ADNI', standardFeature: 'APOE status' },
];

export const demoCases: Record<CaseId, DemoCase> = {
  'CASE-A': {
    id: 'CASE-A',
    shortLabel: 'Case A',
    title: 'Typical known patient',
    description: 'Complete, consistent data that closely resembles the model training distribution.',
    demoPoint: 'Shows how NeuroSage presents a reliable result when evidence is complete, familiar, and consistent.',
    dataStatus: 'Complete',
    patient: { id: 'P001', age: 69, sex: 'Female', educationYears: 16, cohort: 'Memory clinic · Site 01' },
    modalities: [
      { name: 'MRI', status: 'AVAILABLE', summary: 'T1 structural MRI', details: ['Hippocampal volume', 'Cortical thickness', 'Scanner QC passed'] },
      { name: 'Clinical data', status: 'AVAILABLE', summary: 'Complete cognitive and motor battery', details: ['MMSE 23/30', 'MoCA 21/30', 'UPDRS 12', 'Disease history'] },
      { name: 'Biomarkers', status: 'AVAILABLE', summary: 'CSF and plasma measures', details: ['Amyloid elevated', 'Tau elevated', 'CSF ratio available'] },
      { name: 'Genetic data', status: 'AVAILABLE', summary: 'APOE genotyping', details: ['APOE ε4 heterozygous'] },
      { name: 'DaTSCAN', status: 'AVAILABLE', summary: 'Normal striatal uptake pattern', details: ['Bilateral signal available', 'Quality check passed'] },
    ],
    harmonizedFeatures: commonMapping.map((item, index) => ({ ...item, value: ['69', '69', '23', '12', 'ε3/ε4'][index] })),
    adPredictions: [
      { label: 'Alzheimer’s disease', probability: 0.78, safetyStatus: 'TRUST' },
      { label: 'Vascular pathology', probability: 0.22, safetyStatus: 'TRUST' },
      { label: 'Lewy body pathology', probability: 0.18, safetyStatus: 'TRUST' },
    ],
    pdPredictions: [
      { label: 'Parkinson’s disease', probability: 0.24, safetyStatus: 'TRUST' },
      { label: 'Motor impairment risk', probability: 0.31, safetyStatus: 'TRUST' },
    ],
    adFeatures: [
      { label: 'Amyloid level', value: 0.88, direction: 'supports' },
      { label: 'Hippocampal volume', value: 0.72, direction: 'supports' },
      { label: 'MMSE score', value: 0.62, direction: 'supports' },
      { label: 'APOE ε4', value: 0.49, direction: 'supports' },
    ],
    pdFeatures: [
      { label: 'DaTSCAN signal', value: 0.74, direction: 'reduces' },
      { label: 'UPDRS score', value: 0.55, direction: 'reduces' },
      { label: 'Motor features', value: 0.35, direction: 'reduces' },
      { label: 'Age', value: 0.24, direction: 'supports' },
    ],
    safety: {
      overallStatus: 'TRUST',
      reliabilityScore: 0.91,
      signals: [
        safetySignal('dataSufficiency', 'Data sufficiency', 0.98, 'HIGH', 'All expected modalities are present and usable.'),
        safetySignal('distributionConformity', 'Distribution conformity', 0.92, 'HIGH', 'The patient closely resembles known training cohorts.'),
        safetySignal('predictionCertainty', 'Prediction certainty', 0.89, 'HIGH', 'Calibrated outputs remain stable across checks.'),
        safetySignal('modalityAgreement', 'Modality agreement', 0.90, 'HIGH', 'MRI, clinical, and biomarker evidence is consistent.'),
        safetySignal('domainFamiliarity', 'Domain familiarity', 0.94, 'HIGH', 'Site and acquisition characteristics are familiar.'),
        safetySignal('explanationReliability', 'Explanation reliability', 0.91, 'HIGH', 'Feature contributions are stable and clinically coherent.'),
        safetySignal('clinicalHarmRisk', 'Clinical harm risk', 0.18, 'LOW', 'Potential harm from misinterpretation is assessed as low.'),
      ],
      reasons: [
        'All expected modalities are available and passed quality checks.',
        'The patient is familiar relative to the model training distribution.',
        'Disease-model evidence is consistent across modalities.',
      ],
      recommendedAction: 'Use prediction normally with standard clinical interpretation.',
    },
    report: {
      patientSummary: 'The patient demonstrates an Alzheimer’s-related pattern supported by cognitive, MRI, biomarker, and genetic evidence. Parkinsonian evidence is limited.',
      supportingEvidence: ['Reduced hippocampal volume', 'Elevated amyloid and tau biomarkers', 'Reduced MMSE performance', 'APOE ε4 carrier status'],
      safetyConsiderations: ['All expected modalities are available.', 'The patient is familiar to the model domain.', 'Cross-modality agreement and explanation reliability are high.'],
      recommendation: 'The AI findings may be used as supportive evidence with standard clinical interpretation. They do not constitute a diagnosis.',
      sources,
    },
  },
  'CASE-B': {
    id: 'CASE-B',
    shortLabel: 'Case B',
    title: 'Missing modality',
    description: 'DaTSCAN is unavailable, reducing completeness for the Parkinson’s component.',
    demoPoint: 'Shows that the workflow continues without an upload, while the safety gate explicitly lowers reliance.',
    dataStatus: 'DaTSCAN missing',
    patient: { id: 'P002', age: 72, sex: 'Male', educationYears: 12, cohort: 'Neurology clinic · Site 02' },
    modalities: [
      { name: 'MRI', status: 'AVAILABLE', summary: 'T1 structural MRI', details: ['Hippocampal volume', 'White matter features', 'Scanner QC passed'] },
      { name: 'Clinical data', status: 'AVAILABLE', summary: 'Cognitive and motor assessment', details: ['MMSE 20/30', 'MoCA 18/30', 'UPDRS 31', 'Disease history'] },
      { name: 'Biomarkers', status: 'AVAILABLE', summary: 'CSF measures', details: ['Amyloid elevated', 'Tau borderline', 'CSF ratio available'] },
      { name: 'Genetic data', status: 'AVAILABLE', summary: 'APOE genotyping', details: ['APOE ε4 heterozygous'] },
      { name: 'DaTSCAN', status: 'MISSING', summary: 'Imaging not available', details: ['No scan supplied', 'PD analysis uses remaining modalities'] },
    ],
    harmonizedFeatures: commonMapping.map((item, index) => ({ ...item, value: ['72', '72', '20', '31', 'ε3/ε4'][index] })),
    adPredictions: [
      { label: 'Alzheimer’s disease', probability: 0.82, safetyStatus: 'TRUST' },
      { label: 'Vascular pathology', probability: 0.48, safetyStatus: 'CAUTION' },
      { label: 'Lewy body pathology', probability: 0.31, safetyStatus: 'CAUTION' },
    ],
    pdPredictions: [
      { label: 'Parkinson’s disease', probability: 0.71, safetyStatus: 'CAUTION' },
      { label: 'Motor impairment risk', probability: 0.80, safetyStatus: 'CAUTION' },
    ],
    adFeatures: [
      { label: 'Amyloid level', value: 0.91, direction: 'supports' },
      { label: 'Hippocampal volume', value: 0.77, direction: 'supports' },
      { label: 'MMSE score', value: 0.68, direction: 'supports' },
      { label: 'APOE ε4', value: 0.51, direction: 'supports' },
    ],
    pdFeatures: [
      { label: 'UPDRS score', value: 0.87, direction: 'supports' },
      { label: 'Motor features', value: 0.71, direction: 'supports' },
      { label: 'Age', value: 0.42, direction: 'supports' },
      { label: 'DaTSCAN signal', value: 0, direction: 'reduces' },
    ],
    safety: {
      overallStatus: 'CAUTION',
      reliabilityScore: 0.72,
      signals: [
        safetySignal('dataSufficiency', 'Data sufficiency', 0.70, 'MEDIUM', 'DaTSCAN is unavailable for the PD component.'),
        safetySignal('distributionConformity', 'Distribution conformity', 0.88, 'HIGH', 'Available features align with known cohorts.'),
        safetySignal('predictionCertainty', 'Prediction certainty', 0.74, 'MEDIUM', 'PD certainty is reduced without DaTSCAN evidence.'),
        safetySignal('modalityAgreement', 'Modality agreement', 0.65, 'MEDIUM', 'Agreement is based on fewer independent modalities.'),
        safetySignal('domainFamiliarity', 'Domain familiarity', 0.90, 'HIGH', 'The clinical site and cohort are familiar.'),
        safetySignal('explanationReliability', 'Explanation reliability', 0.84, 'HIGH', 'Available feature contributions remain stable.'),
        safetySignal('clinicalHarmRisk', 'Clinical harm risk', 0.35, 'LOW', 'Additional review can mitigate the identified limitation.'),
      ],
      reasons: [
        'DaTSCAN modality is missing.',
        'Parkinson’s evidence is inferred from clinical and motor features only.',
        'Label-level reliability differs between the Alzheimer’s and Parkinson’s outputs.',
      ],
      recommendedAction: 'Use prediction with additional clinical review.',
    },
    report: {
      patientSummary: 'The patient demonstrates patterns associated with Alzheimer’s disease with moderate evidence of Parkinsonian characteristics.',
      supportingEvidence: ['Reduced hippocampal volume', 'Elevated amyloid biomarker', 'Reduced MMSE performance', 'Increased UPDRS motor score'],
      safetyConsiderations: ['DaTSCAN data is unavailable.', 'The Parkinson’s result is based on a reduced modality set.', 'Overall reliability remains sufficient only for cautious use.'],
      recommendation: 'Treat the findings as supportive evidence and obtain additional neurological review or complementary assessment.',
      sources,
    },
  },
  'CASE-C': {
    id: 'CASE-C',
    shortLabel: 'Case C',
    title: 'Unknown / OOD patient',
    description: 'The patient representation differs significantly from the model’s known training distribution.',
    demoPoint: 'A 91% probability is not trusted because familiarity and cross-modality agreement are low.',
    dataStatus: 'Unknown pattern',
    patient: { id: 'P003', age: 74, sex: 'Male', educationYears: 11, cohort: 'External cohort · Novel scanner' },
    modalities: [
      { name: 'MRI', status: 'PARTIAL', summary: 'T1 MRI from unfamiliar scanner', details: ['Hippocampal volume extracted', 'Acquisition profile differs', 'QC review recommended'] },
      { name: 'Clinical data', status: 'AVAILABLE', summary: 'Complete cognitive and motor battery', details: ['MMSE 17/30', 'MoCA 15/30', 'UPDRS 22', 'Atypical disease history'] },
      { name: 'Biomarkers', status: 'AVAILABLE', summary: 'Mixed biomarker profile', details: ['Amyloid elevated', 'Tau normal', 'CSF ratio atypical'] },
      { name: 'Genetic data', status: 'AVAILABLE', summary: 'APOE genotyping', details: ['APOE ε3/ε3'] },
      { name: 'DaTSCAN', status: 'AVAILABLE', summary: 'Asymmetric uptake pattern', details: ['Signal available', 'Pattern differs from known cohort'] },
    ],
    harmonizedFeatures: commonMapping.map((item, index) => ({ ...item, value: ['74', '74', '17', '22', 'ε3/ε3'][index] })),
    adPredictions: [
      { label: 'Alzheimer’s disease', probability: 0.91, safetyStatus: 'DEFER' },
      { label: 'Vascular pathology', probability: 0.42, safetyStatus: 'CAUTION' },
      { label: 'Lewy body pathology', probability: 0.35, safetyStatus: 'DEFER' },
    ],
    pdPredictions: [
      { label: 'Parkinson’s disease', probability: 0.53, safetyStatus: 'DEFER' },
      { label: 'Motor impairment risk', probability: 0.61, safetyStatus: 'CAUTION' },
    ],
    adFeatures: [
      { label: 'Hippocampal volume', value: 0.93, direction: 'supports' },
      { label: 'Amyloid level', value: 0.86, direction: 'supports' },
      { label: 'MMSE score', value: 0.82, direction: 'supports' },
      { label: 'APOE ε4', value: 0.29, direction: 'reduces' },
    ],
    pdFeatures: [
      { label: 'DaTSCAN signal', value: 0.74, direction: 'supports' },
      { label: 'UPDRS score', value: 0.58, direction: 'supports' },
      { label: 'Motor features', value: 0.43, direction: 'supports' },
      { label: 'Age', value: 0.31, direction: 'supports' },
    ],
    safety: {
      overallStatus: 'DEFER',
      reliabilityScore: 0.38,
      signals: [
        safetySignal('dataSufficiency', 'Data sufficiency', 0.94, 'HIGH', 'Most expected information is available.'),
        safetySignal('distributionConformity', 'Distribution conformity', 0.31, 'LOW', 'The representation sits outside known training patterns.'),
        safetySignal('predictionCertainty', 'Prediction certainty', 0.67, 'MEDIUM', 'The headline probability is high but unstable under checks.'),
        safetySignal('modalityAgreement', 'Modality agreement', 0.49, 'LOW', 'MRI, biomarkers, and clinical evidence disagree.'),
        safetySignal('domainFamiliarity', 'Domain familiarity', 0.29, 'LOW', 'Scanner and cohort characteristics are unfamiliar.'),
        safetySignal('explanationReliability', 'Explanation reliability', 0.57, 'MEDIUM', 'Feature importance changes across stability checks.'),
        safetySignal('clinicalHarmRisk', 'Clinical harm risk', 0.78, 'HIGH', 'Misplaced confidence could lead to inappropriate reliance.'),
      ],
      reasons: [
        'Patient representation is significantly outside the known training distribution.',
        'Multiple modalities provide inconsistent evidence.',
        'Domain familiarity is low and the explanation is only moderately stable.',
      ],
      recommendedAction: 'Defer to clinician / additional assessment before relying on this prediction.',
    },
    report: {
      patientSummary: 'The model identified a strong Alzheimer’s-related signal, but the patient appears significantly unfamiliar compared with the data used by the predictive system.',
      supportingEvidence: ['High Alzheimer’s model probability', 'Abnormal MRI-derived features', 'Amyloid-related biomarker signal', 'Reduced cognitive assessment scores'],
      safetyConsiderations: ['Distribution conformity is low.', 'Domain familiarity is low.', 'Cross-modality agreement is weak.', 'The 91% probability should not be interpreted as 91% reliability.'],
      recommendation: 'The prediction should not be relied upon without additional clinical assessment and complementary review.',
      sources,
    },
  },
  'CASE-D': {
    id: 'CASE-D',
    shortLabel: 'Case D',
    title: 'Conflicting modalities',
    description: 'MRI, biomarkers, and clinical observations provide inconsistent disease evidence.',
    demoPoint: 'Shows how modality disagreement lowers safety even when each input is individually available.',
    dataStatus: 'Modality conflict',
    patient: { id: 'P004', age: 66, sex: 'Female', educationYears: 14, cohort: 'Movement clinic · Site 01' },
    modalities: [
      { name: 'MRI', status: 'AVAILABLE', summary: 'Mild structural change', details: ['Hippocampal volume preserved', 'Mild vascular burden', 'Scanner QC passed'] },
      { name: 'Clinical data', status: 'AVAILABLE', summary: 'Marked cognitive and motor findings', details: ['MMSE 19/30', 'MoCA 17/30', 'UPDRS 38', 'Progressive symptoms'] },
      { name: 'Biomarkers', status: 'PARTIAL', summary: 'Mixed CSF profile', details: ['Amyloid normal', 'Tau borderline', 'Repeat sample suggested'] },
      { name: 'Genetic data', status: 'AVAILABLE', summary: 'APOE genotyping', details: ['APOE ε3/ε4'] },
      { name: 'DaTSCAN', status: 'AVAILABLE', summary: 'Reduced striatal uptake', details: ['Bilateral signal reduction', 'Quality check passed'] },
    ],
    harmonizedFeatures: commonMapping.map((item, index) => ({ ...item, value: ['66', '66', '19', '38', 'ε3/ε4'][index] })),
    adPredictions: [
      { label: 'Alzheimer’s disease', probability: 0.67, safetyStatus: 'CAUTION' },
      { label: 'Vascular pathology', probability: 0.54, safetyStatus: 'CAUTION' },
      { label: 'Lewy body pathology', probability: 0.58, safetyStatus: 'CAUTION' },
    ],
    pdPredictions: [
      { label: 'Parkinson’s disease', probability: 0.74, safetyStatus: 'CAUTION' },
      { label: 'Motor impairment risk', probability: 0.83, safetyStatus: 'CAUTION' },
    ],
    adFeatures: [
      { label: 'MMSE score', value: 0.81, direction: 'supports' },
      { label: 'APOE ε4', value: 0.54, direction: 'supports' },
      { label: 'Amyloid level', value: 0.63, direction: 'reduces' },
      { label: 'Hippocampal volume', value: 0.58, direction: 'reduces' },
    ],
    pdFeatures: [
      { label: 'UPDRS score', value: 0.90, direction: 'supports' },
      { label: 'DaTSCAN signal', value: 0.86, direction: 'supports' },
      { label: 'Motor features', value: 0.75, direction: 'supports' },
      { label: 'Age', value: 0.22, direction: 'supports' },
    ],
    safety: {
      overallStatus: 'CAUTION',
      reliabilityScore: 0.64,
      signals: [
        safetySignal('dataSufficiency', 'Data sufficiency', 0.90, 'HIGH', 'All core modality groups are represented.'),
        safetySignal('distributionConformity', 'Distribution conformity', 0.86, 'HIGH', 'The patient remains within a familiar data region.'),
        safetySignal('predictionCertainty', 'Prediction certainty', 0.62, 'MEDIUM', 'Competing disease signals broaden uncertainty.'),
        safetySignal('modalityAgreement', 'Modality agreement', 0.28, 'LOW', 'MRI, biomarkers, and clinical findings conflict.'),
        safetySignal('domainFamiliarity', 'Domain familiarity', 0.91, 'HIGH', 'Cohort and acquisition environment are familiar.'),
        safetySignal('explanationReliability', 'Explanation reliability', 0.59, 'MEDIUM', 'Explanations remain sensitive to modality weighting.'),
        safetySignal('clinicalHarmRisk', 'Clinical harm risk', 0.52, 'MEDIUM', 'The conflict could lead to over-specific interpretation.'),
      ],
      reasons: [
        'MRI suggests limited neurodegeneration while cognitive findings are marked.',
        'Biomarker evidence does not align with the Alzheimer’s model output.',
        'The Parkinson’s component is stronger than the structural MRI evidence.',
      ],
      recommendedAction: 'Use prediction with additional clinical review.',
    },
    report: {
      patientSummary: 'The patient presents mixed Alzheimer’s, vascular, Lewy body, and Parkinsonian signals, with clinically important disagreement across modalities.',
      supportingEvidence: ['Increased UPDRS motor score', 'Reduced DaTSCAN uptake', 'Reduced cognitive assessment performance', 'Mild vascular MRI burden'],
      safetyConsiderations: ['Modality agreement is low.', 'Biomarker and structural evidence conflict with clinical findings.', 'Explanation stability is moderate.'],
      recommendation: 'Use the combined findings cautiously and resolve the cross-modality discrepancy through specialist review and repeat assessment.',
      sources,
    },
  },
};

export const caseList = Object.values(demoCases);

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

export const dashboardRecentCases = caseList.map((item) => ({
  patient: item.patient.id,
  dataStatus: item.dataStatus,
  adStatus: 'Completed',
  pdStatus: 'Completed',
  safetyStatus: item.safety.overallStatus,
}));

export function isCaseId(value: string): value is CaseId {
  return value in demoCases;
}

export function isAssessmentStage(value: string): value is AssessmentStage {
  return assessmentStages.some((stage) => stage.key === value);
}

export function caseHref(caseId: CaseId, stage: AssessmentStage): string {
  return `/assessment/${caseId}/${stage}`;
}
