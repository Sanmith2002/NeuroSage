'use client';

import { useSyncExternalStore } from 'react';

import { analyzeMri, assess, predictDemoMri, type MriProgress } from '@/lib/ad/api';
import type {
  ClinicalRequest,
  LabelResult,
  MriFields,
  MriResult,
  MriStage,
  ReliabilityKey,
  ReliabilitySignal,
  SharedDocument,
} from '@/lib/ad/types';
import type { CaseView, SafetySignal, SafetyStatus, SignalLevel } from '@/lib/assessment';

// Live cases live in a module-level store mirrored to sessionStorage, so an MRI stream started on the
// form keeps updating the case after the router moves on. Nothing is sent anywhere except the AD service.

export interface LiveMriState {
  status: 'idle' | 'running' | 'merging' | 'done' | 'error';
  source: 'upload' | 'demo';
  label?: string;
  stage?: MriStage;
  progress?: number;
  error?: string;
}

export interface LiveCase {
  id: string;
  createdAt: string;
  request: ClinicalRequest;
  document: SharedDocument;
  mriFields?: MriFields;
  mri?: LiveMriState;
}

const STORAGE_KEY = 'neurosage.live-cases.v1';
const LIVE_PREFIX = 'LIVE-';
type Store = Record<string, LiveCase>;

let store: Store = {};
let loaded = false;
const listeners = new Set<() => void>();
const EMPTY: Store = {};

function load(): void {
  if (loaded || typeof window === 'undefined') return;
  loaded = true;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (raw) store = JSON.parse(raw) as Store;
    // a page reload kills any in-flight MRI stream
    for (const c of Object.values(store)) {
      if (c.mri && (c.mri.status === 'running' || c.mri.status === 'merging')) {
        c.mri = { ...c.mri, status: 'error', error: 'The MRI analysis was interrupted by a page reload.' };
      }
    }
  } catch {
    store = {};
  }
}

function persist(): void {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // storage full or blocked: the in-memory store still works for this tab
  }
}

function emit(): void {
  persist();
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function snapshot(): Store {
  load();
  return store;
}

export function isLiveCaseId(id: string): boolean {
  return id.startsWith(LIVE_PREFIX);
}

export function getLiveCase(id: string): LiveCase | undefined {
  load();
  return store[id];
}

export function useLiveCases(): Store {
  return useSyncExternalStore(subscribe, snapshot, () => EMPTY);
}

export function useLiveCase(id: string | undefined): LiveCase | undefined {
  const all = useLiveCases();
  return id ? all[id] : undefined;
}

function shortId(): string {
  const bytes = new Uint8Array(4);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(36).padStart(2, '0')).join('').slice(0, 6).toUpperCase();
}

export function addLiveCase(request: ClinicalRequest, document: SharedDocument, mriFields?: MriFields): LiveCase {
  load();
  const id = `${LIVE_PREFIX}${shortId()}`;
  const c: LiveCase = { id, createdAt: new Date().toISOString(), request, document, mriFields };
  store = { ...store, [id]: c };
  emit();
  return c;
}

function patch(id: string, update: (c: LiveCase) => Partial<LiveCase>): void {
  const c = store[id];
  if (!c) return;
  store = { ...store, [id]: { ...c, ...update(c) } };
  emit();
}

function patchMri(id: string, mri: Partial<LiveMriState>): void {
  patch(id, (c) => ({ mri: { ...(c.mri ?? { status: 'idle', source: 'upload' }), ...mri } }));
}

async function mergeMri(id: string, result: MriResult): Promise<void> {
  const c = store[id];
  if (!c) return;
  patchMri(id, { status: 'merging', stage: 'explain', progress: 1 });
  const document = await assess(c.request, result);
  patch(id, () => ({ document }));
  patchMri(id, { status: 'done' });
}

/** Streams the MRI analysis, then merges it into the case through /v1/assess. */
export async function runMriUpload(id: string, file: File, fields: MriFields): Promise<void> {
  patch(id, () => ({ mriFields: fields }));
  patchMri(id, { status: 'running', source: 'upload', label: file.name, stage: 'upload', progress: 0, error: undefined });
  try {
    const result = await analyzeMri(file, fields, {
      onStage: (p: MriProgress) => patchMri(id, { stage: p.stage, progress: p.progress }),
    });
    await mergeMri(id, result);
  } catch (err) {
    patchMri(id, { status: 'error', error: err instanceof Error ? err.message : 'MRI analysis failed' });
  }
}

export async function runMriDemo(id: string, demoId: string, fields: MriFields | null): Promise<void> {
  patchMri(id, { status: 'running', source: 'demo', label: demoId, stage: 'predict', progress: 0.5, error: undefined });
  try {
    const result = await predictDemoMri(demoId, fields);
    await mergeMri(id, result);
  } catch (err) {
    patchMri(id, { status: 'error', error: err instanceof Error ? err.message : 'MRI prediction failed' });
  }
}

// ------------------------------------------------------------------ view model
export const SIGNAL_LABELS: Record<ReliabilityKey, string> = {
  dataSufficiency: 'Data sufficiency',
  distributionConformity: 'Distribution conformity',
  predictionCertainty: 'Prediction certainty',
  modalityAgreement: 'Modality agreement',
  domainFamiliarity: 'Domain familiarity',
  explanationReliability: 'Explanation reliability',
  clinicalHarmRisk: 'Clinical harm risk',
};

export const SIGNAL_ORDER = Object.keys(SIGNAL_LABELS) as ReliabilityKey[];

export function signalLevel(score: number): SignalLevel {
  return score >= 0.7 ? 'HIGH' : score >= 0.4 ? 'MEDIUM' : 'LOW';
}

/** PLACEHOLDER for the Safety component's gate (IT23147850): any signal < 0.4 → DEFER, any < 0.7 → CAUTION. */
export function provisionalStatus(doc: SharedDocument): SafetyStatus {
  const scores = SIGNAL_ORDER.map((k) => doc.reliability_signals[k])
    .filter((s): s is ReliabilitySignal => s != null && isScored(s))
    .map((s) => s.score);
  if (scores.some((s) => s < 0.4)) return 'DEFER';
  if (scores.some((s) => s < 0.7)) return 'CAUTION';
  return 'TRUST';
}

function isScored(s: ReliabilitySignal): boolean {
  return typeof s.score === 'number' && Number.isFinite(s.score);
}

export function naccLabels(doc: SharedDocument): LabelResult[] {
  return doc.labels.filter((l) => l.source === 'clinical');
}

export function mriLabels(doc: SharedDocument): LabelResult[] {
  return doc.labels.filter((l) => l.source !== 'clinical');
}

const pct = (p: number) => `${Math.round(p * 100)}%`;

function recommendedAction(status: SafetyStatus): string {
  if (status === 'TRUST') return 'Provisional: use as supportive research evidence with standard clinical interpretation.';
  if (status === 'CAUTION') return 'Provisional: review the flagged limitations and obtain additional clinical assessment.';
  return 'Provisional: do not rely on this output without additional assessment.';
}

export function reportSummary(c: LiveCase) {
  const doc = c.document;
  const labels = naccLabels(doc);
  const positive = labels.filter((l) => l.predicted);
  const status = provisionalStatus(doc);
  const patientSummary = positive.length
    ? `The clinical co-pathology model places this patient above threshold for ${positive.map((l) => l.label).join(' and ')}` +
      `${positive.length > 1 ? ' (co-pathology pattern)' : ''}. These estimates refer to autopsy neuropathology risk, not a clinical diagnosis.`
    : 'The clinical co-pathology model does not place this patient above threshold for Alzheimer’s, Lewy body or vascular pathology. These estimates refer to autopsy neuropathology risk, not a clinical diagnosis.';

  const supportingEvidence: string[] = [];
  for (const l of labels) {
    const top = (l.explanation?.top ?? []).filter((t) => t.direction === 'supports').slice(0, 3);
    if (top.length) supportingEvidence.push(`${l.label} (${pct(l.probability)}): ${top.map((t) => t.display_name).join(', ')}`);
  }
  for (const l of mriLabels(doc)) {
    supportingEvidence.push(`${l.label}: ${pct(l.probability)} (threshold ${pct(l.threshold)})`);
  }
  if (!supportingEvidence.length) supportingEvidence.push('Explanations were not requested for this assessment.');

  const safetyConsiderations = SIGNAL_ORDER.flatMap((k) => {
    const s = doc.reliability_signals[k];
    return s && s.score < 0.7 ? [`${SIGNAL_LABELS[k]} ${s.score.toFixed(2)}: ${s.detail}`] : [];
  });
  safetyConsiderations.push(...doc.warnings);

  return {
    status,
    patientSummary,
    supportingEvidence,
    safetyConsiderations,
    recommendation: `${recommendedAction(status)} ${doc.disclaimer}`,
  };
}

function modalitySummaryDetails(c: LiveCase, name: string): string[] {
  const last = c.request.visits[c.request.visits.length - 1];
  const p = c.request.patient;
  if (name === 'Clinical data') {
    const d: string[] = [];
    if (last.mmse != null) d.push(`MMSE ${last.mmse}/30 (last visit)`);
    if (last.moca != null) d.push(`MoCA ${last.moca}/30 (last visit)`);
    if (last.cognition_untestable) d.push('Cognition untestable at last visit');
    if (last.cdr_sum != null) d.push(`CDR-SB ${last.cdr_sum}`);
    if (last.gds != null) d.push(`GDS ${last.gds}/15`);
    return d.length ? d : ['Cognitive scores not entered'];
  }
  if (name === 'Genetic data') return [p.apoe_e4_count == null ? 'APOE unknown' : `APOE ε4 alleles: ${p.apoe_e4_count}`];
  if (name === 'Biomarkers') {
    const csf = c.request.csf;
    if (!csf) return ['No CSF values'];
    return [
      csf.abeta42 != null ? `Aβ42 ${csf.abeta42}` : 'Aβ42 not entered',
      csf.ptau181 != null ? `p-tau181 ${csf.ptau181}` : 'p-tau181 not entered',
      csf.ttau != null ? `t-tau ${csf.ttau}` : 't-tau not entered',
    ];
  }
  if (name === 'MRI') {
    const m = c.document.mri;
    if (m?.qc) return [`Brain volume ${m.qc.brain_cm3 ?? '—'} cm³`, `MNI Dice ${m.qc.dice_mni ?? '—'}`, `Registration ${m.qc.registration ?? '—'}`];
    if (c.mri?.status === 'running' || c.mri?.status === 'merging') return ['Analysis in progress'];
    if (m) return ['Demo volume (preprocessed)'];
    return ['No scan analysed'];
  }
  return [];
}

/** Maps a model-backed case onto the shared CaseView used by the shell, stepper and dashboard. */
export function toViewModel(c: LiveCase): CaseView {
  const doc = c.document;
  const status = provisionalStatus(doc);
  const last = c.request.visits[c.request.visits.length - 1];
  const p = c.request.patient;
  const signals: SafetySignal[] = SIGNAL_ORDER.flatMap((k) => {
    const s = doc.reliability_signals[k];
    return s && isScored(s) ? [{ key: k, label: SIGNAL_LABELS[k], score: s.score, level: signalLevel(s.score), description: s.detail }] : [];
  });
  const scores = signals.map((s) => s.score);
  const missing = doc.modalities.filter((m) => m.status !== 'AVAILABLE').map((m) => m.name);

  return {
    id: c.id,
    createdAt: c.createdAt,
    shortLabel: 'AD assessment',
    title: 'AD co-pathology assessment',
    note: 'Output of the trained AD co-pathology models running on this computer. Safety status is provisional; the PD component is not connected.',
    dataStatus: missing.length ? `${missing.join(', ')} missing` : 'Complete',
    patient: {
      id: p.id || 'anonymous',
      age: last.age,
      sex: p.sex ? p.sex[0].toUpperCase() + p.sex.slice(1) : 'Unknown',
      educationYears: p.education_years ?? Number.NaN,
      cohort: 'Entered in this browser tab · not stored on the server',
    },
    modalities: doc.modalities.map((m) => ({
      name: m.name,
      status: m.status,
      summary: m.detail,
      details: modalitySummaryDetails(c, m.name),
    })),
    adPredictions: naccLabels(doc).map((l) => ({ label: l.label, probability: l.probability, safetyStatus: status })),
    safety: {
      overallStatus: status,
      reliabilityScore: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0,
      signals,
    },
  };
}
