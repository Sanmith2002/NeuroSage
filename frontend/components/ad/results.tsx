'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Dna,
  Download,
  FlaskConical,
  Gauge,
  Info,
  LayoutDashboard,
  LoaderCircle,
  Microscope,
  Plug,
  Printer,
  ScanLine,
  ShieldAlert,
  Stethoscope,
  TableProperties,
  TriangleAlert,
  UserRound,
} from 'lucide-react';
import { Bar, BarChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ModalityStatus, SafetySignalCard } from '@/components/platform/neurosage-pages';
import { AssessmentStepper, PageHeader, StageActions, StatusBadge, statusTone } from '@/components/platform/neurosage-ui';
import { artifactUrl, getModels, isLiveEnabled } from '@/lib/ad/api';
import { DISCLAIMER, type LabelResult, type ShapFeature, type SharedDocument } from '@/lib/ad/types';
import {
  SIGNAL_LABELS,
  SIGNAL_ORDER,
  mriLabels,
  naccLabels,
  provisionalStatus,
  reportSummary,
  signalLevel,
  type LiveCase,
} from '@/lib/ad/live-cases';
import type { AssessmentStage, CaseView } from '@/lib/assessment';

// Validated diverging pair for the SHAP chart (dataviz validator: CVD ΔE ≥ 21, contrast ≥ 3:1).
const SUPPORTS = '#2a78c2';
const REDUCES = '#b07a2a';
const pct = (p: number) => `${Math.round(p * 100)}%`;

const MRI_STAGES: Array<{ key: string; label: string }> = [
  { key: 'upload', label: 'Uploading' },
  { key: 'convert', label: 'Converting' },
  { key: 'skullstrip', label: 'Skull stripping' },
  { key: 'bias', label: 'Bias correction' },
  { key: 'register', label: 'MNI registration' },
  { key: 'normalise', label: 'Normalising' },
  { key: 'predict', label: 'Predicting' },
  { key: 'explain', label: 'Explaining' },
];

const modalityIcons: Record<string, typeof ScanLine> = {
  MRI: ScanLine,
  'Clinical data': ClipboardCheck,
  Biomarkers: FlaskConical,
  'Genetic data': Dna,
};

// ------------------------------------------------------------------ shared pieces
export function ResearchDisclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <p className={`live-disclaimer ${compact ? 'is-compact' : ''}`} role="note">
      <ShieldAlert aria-hidden="true" />
      <strong>{DISCLAIMER}</strong>
    </p>
  );
}

function ProvisionalBadge({ doc }: { doc: SharedDocument }) {
  return (
    <span className="live-provisional">
      <StatusBadge status={provisionalStatus(doc)} />
      <small>Provisional (AD component only)</small>
    </span>
  );
}

function LiveLead({ item, live, stage }: { item: CaseView; live: LiveCase; stage: AssessmentStage }) {
  return (
    <>
      <AssessmentStepper currentCase={item} stage={stage} />
      <div className={`case-lead tone-${statusTone(item.safety.overallStatus)}`}>
        <div><span>Live case · {live.id}</span><strong>{item.title}</strong><small>{item.note}</small></div>
        <ProvisionalBadge doc={live.document} />
      </div>
      <ResearchDisclaimer compact />
    </>
  );
}

function MriProgressBanner({ live }: { live: LiveCase }) {
  const m = live.mri;
  if (!m || m.status === 'idle' || m.status === 'done') return null;
  if (m.status === 'error') {
    return (
      <aside className="live-banner tone-defer" role="alert">
        <CircleAlert aria-hidden="true" />
        <p><strong>MRI analysis failed.</strong> {m.error} Clinical results below are unaffected.</p>
      </aside>
    );
  }
  const idx = MRI_STAGES.findIndex((s) => s.key === m.stage);
  const label = m.status === 'merging' ? 'Merging MRI with clinical results' : m.stage === 'queued' ? 'Waiting for the MRI worker' : MRI_STAGES[idx]?.label ?? 'Working';
  return (
    <aside className="live-banner" aria-live="polite">
      <LoaderCircle className="animate-spin" aria-hidden="true" />
      <div>
        <p><strong>MRI analysis running</strong> · {label}… ({Math.round((m.progress ?? 0) * 100)}%)</p>
        <ol className="live-stage-list" aria-label="MRI pipeline stages">
          {MRI_STAGES.map((s, i) => (
            <li key={s.key} className={i < idx ? 'is-done' : i === idx ? 'is-current' : ''}>{s.label}</li>
          ))}
        </ol>
        <small>Preprocessing takes about 2–4 minutes on the server. You can keep browsing this case.</small>
      </div>
    </aside>
  );
}

// ------------------------------------------------------------------ probability bars
function LabelBar({ label }: { label: LabelResult }) {
  const p = label.probability;
  const sd = label.uncertainty?.fold_sd ?? null;
  const lo = sd != null ? Math.max(0, p - sd) : null;
  const hi = sd != null ? Math.min(1, p + sd) : null;
  return (
    <div className="live-prob-row">
      <div className="live-prob-head">
        <span>{label.label}</span>
        <strong>{pct(p)}</strong>
        <span className={`live-call ${label.predicted ? 'is-positive' : 'is-negative'}`}>
          {label.predicted ? <CheckCircle2 aria-hidden="true" /> : <span aria-hidden="true">–</span>}
          {label.predicted ? 'Above threshold' : 'Below threshold'}
        </span>
      </div>
      <span className="sr-only">{`${label.label}: probability ${pct(p)}, threshold ${pct(label.threshold)}${sd != null ? `, fold SD ${sd.toFixed(3)}` : ''}`}</span>
      <div className="live-prob-track" aria-hidden="true">
        <i className={label.predicted ? 'is-positive' : ''} style={{ width: `${p * 100}%` }} />
        {lo != null && hi != null && <b className="live-whisker" style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }} />}
        <em className="live-threshold" style={{ left: `${label.threshold * 100}%` }} />
      </div>
      <small className="live-prob-meta">
        Threshold {pct(label.threshold)}
        {sd != null && <> · fold SD ±{(sd * 100).toFixed(1)} pts</>}
        {label.uncertainty?.margin != null && <> · margin {(label.uncertainty.margin * 100).toFixed(1)} pts</>}
        {label.performance?.test_auroc != null && (
          <> · test AUROC {label.performance.test_auroc.toFixed(3)}
            {label.performance.test_auroc_ci && ` [${label.performance.test_auroc_ci[0].toFixed(3)}–${label.performance.test_auroc_ci[1].toFixed(3)}]`}</>
        )}
      </small>
    </div>
  );
}

function ShapTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ShapFeature & { name: string } }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="live-tooltip">
      <strong>{d.display_name}</strong>
      <span>Entered value: {d.value == null ? 'missing (imputed)' : Number(d.value.toFixed(3))}</span>
      <span>SHAP {d.shap > 0 ? '+' : ''}{d.shap.toFixed(4)} · {d.direction}</span>
    </div>
  );
}

export function ShapChart({ label }: { label: LabelResult }) {
  const top = label.explanation?.top ?? [];
  if (!top.length) return <p className="live-muted">Explanation not requested.</p>;
  // split into two stacked series so each sign gets its own colour without per-cell overrides
  const data = top.map((t) => ({ ...t, name: t.display_name, supports: t.shap > 0 ? t.shap : 0, reduces: t.shap > 0 ? 0 : t.shap }));
  const max = Math.max(...top.map((t) => Math.abs(t.shap)), 1e-9);
  return (
    <figure className="live-shap">
      <figcaption>
        <span><strong>{label.label}</strong> · top {top.length} contributions</span>
        <span className="live-legend">
          <span><i style={{ background: SUPPORTS }} />Supports</span>
          <span><i style={{ background: REDUCES }} />Reduces</span>
        </span>
      </figcaption>
      <div style={{ width: '100%', height: data.length * 30 + 30 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 4 }} barCategoryGap={6}>
            <XAxis type="number" domain={[-max, max]} tick={{ fontSize: 9, fill: '#708397' }} tickFormatter={(v: number) => v.toFixed(2)} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 9, fill: '#3a5167' }} axisLine={false} tickLine={false} interval={0} />
            <ReferenceLine x={0} stroke="#9fb0c0" />
            <Tooltip content={<ShapTooltip />} cursor={{ fill: 'rgb(31 54 81 / 5%)' }} />
            <Bar dataKey="supports" stackId="shap" fill={SUPPORTS} radius={4} isAnimationActive={false} />
            <Bar dataKey="reduces" stackId="shap" fill={REDUCES} radius={4} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="sr-only">
      <table>
        <caption>{label.label} SHAP contributions</caption>
        <thead><tr><th>Feature</th><th>Value</th><th>SHAP</th><th>Direction</th></tr></thead>
        <tbody>{top.map((t) => <tr key={t.feature}><td>{t.display_name}</td><td>{t.value == null ? 'missing' : Number(t.value.toFixed(3))}</td><td>{t.shap.toFixed(4)}</td><td>{t.direction}</td></tr>)}</tbody>
      </table>
      </div>
      <small className="live-muted">
        Scale: {label.explanation?.scale === 'log-odds' ? 'log-odds (XGBoost)' : 'raw probability (Random Forest)'} · global stability Spearman {label.explanation?.stability_spearman?.toFixed(2) ?? '—'}
      </small>
    </figure>
  );
}

// ------------------------------------------------------------------ MRI panel
function MriPanel({ live }: { live: LiveCase }) {
  const doc = live.document;
  const labels = mriLabels(doc);
  const mri = doc.mri;
  const running = live.mri && (live.mri.status === 'running' || live.mri.status === 'merging');
  const cam = artifactUrl(mri?.gradcam_png);
  const [camFailed, setCamFailed] = useState(false);

  return (
    <section className="live-subpanel" aria-labelledby="mri-heading">
      <h3 id="mri-heading"><ScanLine aria-hidden="true" />MRI (ADNI models)</h3>
      {!labels.length && !running && (
        <p className="live-muted">No MRI analysed for this case. Add a T1 scan from the live form to get MRI-based outputs.</p>
      )}
      {running && !labels.length && <p className="live-muted">Waiting for the MRI analysis to finish…</p>}
      {labels.length > 0 && (
        <>
          <div className="probability-list">{labels.map((l) => <LabelBar key={l.key} label={l} />)}</div>
          {labels.some((l) => l.note) && <p className="live-muted">{labels.find((l) => l.note)?.note}</p>}
          {mri?.attention && (
            <div className="live-attention">
              <span>Fusion attention</span>
              <div aria-hidden="true"><i style={{ width: `${mri.attention.mri * 100}%` }} /><b style={{ width: `${mri.attention.tabular * 100}%` }} /></div>
              <small>MRI {pct(mri.attention.mri)} · tabular {pct(mri.attention.tabular)}</small>
            </div>
          )}
          {cam && !camFailed && (
            <figure className="live-cam">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={cam} alt="Grad-CAM attention overlaid on sagittal, coronal and axial mid-slices" onError={() => setCamFailed(true)} />
              <figcaption>Model attention, not a lesion map.</figcaption>
            </figure>
          )}
          {camFailed && <p className="live-muted">The Grad-CAM image has expired (kept 30 minutes in server memory).</p>}
          {mri?.qc && (
            <dl className="live-qc">
              <div><dt>Brain volume</dt><dd>{mri.qc.brain_cm3 ?? '—'} cm³</dd></div>
              <div><dt>MNI Dice</dt><dd>{mri.qc.dice_mni?.toFixed(3) ?? '—'}</dd></div>
              <div><dt>Registration</dt><dd>{mri.qc.registration ?? '—'}</dd></div>
              <div><dt>QC</dt><dd>{mri.qc.passed ? 'Passed' : 'Failed'}</dd></div>
            </dl>
          )}
          {mri?.source === 'demo' && <p className="live-muted">Demo volume from the locked ADNI test set (already preprocessed).</p>}
        </>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ pages
export function LivePatientPage({ item, live }: { item: CaseView; live: LiveCase }) {
  const p = live.request.patient;
  return (
    <div className="page-content assessment-page">
      <LiveLead item={item} live={live} stage="patient" />
      <PageHeader
        eyebrow="Step 1 · Patient input"
        title="Patient assessment"
        description="The data entered for this live assessment. It is kept only in this browser tab."
        aside={<span className="patient-id"><UserRound aria-hidden="true" />{item.patient.id}</span>}
      />
      <MriProgressBanner live={live} />
      <section className="patient-summary-band" aria-labelledby="patient-details-heading">
        <div><p className="eyebrow">Patient information</p><h2 id="patient-details-heading">{item.patient.id}</h2><span>{item.patient.cohort}</span></div>
        <dl>
          <div><dt>Age (last visit)</dt><dd>{item.patient.age}</dd></div>
          <div><dt>Sex</dt><dd>{item.patient.sex}</dd></div>
          <div><dt>Education</dt><dd>{p.education_years != null ? `${p.education_years} years` : 'Unknown'}</dd></div>
          <div><dt>Visits</dt><dd>{live.request.visits.length}</dd></div>
        </dl>
      </section>

      <section className="content-section" aria-labelledby="modalities-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Modality status</p><h2 id="modalities-heading">Available patient data</h2></div>
          <p>Missing inputs lower the data-sufficiency signal; the model imputes them.</p>
        </div>
        <div className="modality-grid live-modality-grid">
          {item.modalities.map((m) => {
            const Icon = modalityIcons[m.name] ?? TableProperties;
            return (
              <article className={`modality-card modality-${m.status.toLowerCase()}`} key={m.name}>
                <div className="modality-heading">
                  <span className="modality-icon"><Icon aria-hidden="true" /></span>
                  <div><h3>{m.name}</h3><p>{m.summary}</p></div>
                  <ModalityStatus modality={m} />
                </div>
                <ul>{m.details.map((d) => <li key={d}><CheckCircle2 aria-hidden="true" />{d}</li>)}</ul>
              </article>
            );
          })}
        </div>
      </section>

      <section className="content-section" aria-labelledby="visits-heading">
        <div className="section-heading compact"><div><p className="eyebrow">Entered visits</p><h2 id="visits-heading">Clinical visits</h2></div></div>
        <div className="table-surface live-scroll">
          <Table>
            <TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Age</TableHead><TableHead>MMSE</TableHead><TableHead>MoCA</TableHead><TableHead>CDR global</TableHead><TableHead>CDR-SB</TableHead><TableHead>GDS</TableHead><TableHead>BMI</TableHead><TableHead>SBP</TableHead></TableRow></TableHeader>
            <TableBody>
              {live.request.visits.map((v) => (
                <TableRow key={v.date}>
                  <TableCell className="font-semibold text-slate-800">{v.date}</TableCell>
                  <TableCell>{v.age}</TableCell>
                  <TableCell>{v.cognition_untestable ? 'Untestable' : v.mmse ?? '—'}</TableCell>
                  <TableCell>{v.cognition_untestable ? 'Untestable' : v.moca ?? '—'}</TableCell>
                  <TableCell>{v.cdr_global ?? '—'}</TableCell>
                  <TableCell>{v.cdr_sum ?? '—'}</TableCell>
                  <TableCell>{v.gds ?? '—'}</TableCell>
                  <TableCell>{v.bmi ?? '—'}</TableCell>
                  <TableCell>{v.bp_systolic ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
      <StageActions currentCase={item} stage="patient" nextLabel="Review harmonization" />
    </div>
  );
}

const DERIVED_LABELS: Record<string, string> = {
  n_visits: 'Number of visits',
  followup_years: 'Follow-up (years)',
  age_first_visit: 'Age at first visit',
  lastavail_MMSE_EQ: 'Most recent MMSE (harmonised)',
  years_since_MMSE_EQ: 'Years since last cognitive test',
  slope_MMSE_EQ: 'MMSE slope / year',
  slope_CDRSUM: 'CDR-SB slope / year',
  slope_NACCGDS: 'GDS slope / year',
  delta_MMSE_EQ: 'MMSE change, first → last',
  delta_CDRSUM: 'CDR-SB change, first → last',
  delta_NACCGDS: 'GDS change, first → last',
  csf_ptau_abeta: 'CSF p-tau / Aβ42',
  csf_ttau_abeta: 'CSF t-tau / Aβ42',
};

export function LiveHarmonizationPage({ item, live }: { item: CaseView; live: LiveCase }) {
  const doc = live.document;
  const derived = doc.derived_features ?? {};
  return (
    <div className="page-content assessment-page">
      <LiveLead item={item} live={live} stage="harmonization" />
      <PageHeader
        eyebrow="Step 2 · Standardization"
        title="Data harmonization"
        description="Entered values mapped onto the NACC training representation, plus the longitudinal features derived from the visit history."
      />
      <MriProgressBanner live={live} />
      <div className="two-column-content harmonization-content live-two-col">
        <section aria-labelledby="mapping-heading">
          <div className="section-heading compact"><div><p className="eyebrow">Cognition crosswalk</p><h2 id="mapping-heading">Original → standard</h2></div></div>
          <div className="table-surface live-scroll">
            <Table>
              <TableHeader><TableRow><TableHead>Visit</TableHead><TableHead>Original</TableHead><TableHead>Standard</TableHead><TableHead>Rule</TableHead></TableRow></TableHeader>
              <TableBody>
                {doc.harmonisation_log.map((h, i) => (
                  <TableRow key={`${h.visit}-${i}`}>
                    <TableCell className="font-mono text-xs">{h.visit ?? '—'}</TableCell>
                    <TableCell>{h.original}</TableCell>
                    <TableCell className="font-semibold text-slate-800">{h.standard}</TableCell>
                    <TableCell>{h.rule}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
        <section aria-labelledby="derived-heading">
          <div className="section-heading compact"><div><p className="eyebrow">Longitudinal</p><h2 id="derived-heading">Derived features</h2></div></div>
          <div className="readiness-list">
            {Object.entries(DERIVED_LABELS).map(([k, label]) => {
              const v = derived[k];
              return (
                <div key={k}>
                  <span>{label}</span>
                  <span className={v == null ? 'live-muted' : 'live-value'}>{v == null ? 'Missing' : Number(v.toFixed(3))}</span>
                </div>
              );
            })}
          </div>
        </section>
      </div>
      <WarningList warnings={doc.warnings} />
      <StageActions currentCase={item} stage="harmonization" nextLabel="Continue to AI analysis" />
    </div>
  );
}

function WarningList({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <section className="content-section" aria-labelledby="warnings-heading">
      <div className="section-heading compact"><div><p className="eyebrow">Caveats</p><h2 id="warnings-heading">Warnings</h2></div></div>
      <div className="reason-list">{warnings.map((w) => <div key={w}><TriangleAlert aria-hidden="true" /><p>{w}</p></div>)}</div>
    </section>
  );
}

export function LivePredictionsPage({ item, live }: { item: CaseView; live: LiveCase }) {
  const doc = live.document;
  const labels = naccLabels(doc);
  const positive = labels.filter((l) => l.predicted);
  const [shapKey, setShapKey] = useState(labels[0]?.key);
  const shapLabel = labels.find((l) => l.key === shapKey) ?? labels[0];

  return (
    <div className="page-content assessment-page predictions-page">
      <LiveLead item={item} live={live} stage="predictions" />
      <PageHeader
        eyebrow="Step 3 · Live model inference"
        title="Disease analysis"
        description="Independent, calibrated probabilities from the AD co-pathology component. Labels are multi-label: they do not sum to 1."
      />
      <MriProgressBanner live={live} />

      <div className="model-grid live-model-grid">
        <article className="model-panel model-ad">
          <header className="model-header">
            <span><BrainCircuit aria-hidden="true" /></span>
            <div><p>Component 1 · live</p><h2>Alzheimer’s &amp; co-pathology</h2><small>{doc.component.models.clinical} · autopsy-pathology targets</small></div>
          </header>
          <section>
            <h3>Prediction results</h3>
            <div className="probability-list">{labels.map((l) => <LabelBar key={l.key} label={l} />)}</div>
            <p className="live-copath">
              <strong>Co-pathology summary:</strong>{' '}
              {positive.length === 0 ? 'no label above threshold.' : `${positive.map((l) => l.label).join(' + ')} above threshold${positive.length > 1 ? ' (mixed pathology).' : '.'}`}
            </p>
          </section>
          <section className="explanation-section">
            <h3>Prediction explanation (SHAP)</h3>
            <div className="live-tabs" role="tablist" aria-label="Explained label">
              {labels.map((l) => (
                <button key={l.key} role="tab" type="button" aria-selected={l.key === shapLabel?.key} className={l.key === shapLabel?.key ? 'is-active' : ''} onClick={() => setShapKey(l.key)}>
                  {l.label}
                </button>
              ))}
            </div>
            {shapLabel && <ShapChart label={shapLabel} />}
          </section>
          <MriPanel live={live} />
        </article>

        <article className="model-panel model-pd">
          <header className="model-header">
            <span><Activity aria-hidden="true" /></span>
            <div><p>Component 2</p><h2>Parkinson’s disease</h2><small>Owned by another team member</small></div>
          </header>
          <section className="live-empty">
            <Plug aria-hidden="true" />
            <strong>PD component not connected</strong>
            <p>Live assessments only include the AD co-pathology component. No Parkinson’s output is shown or inferred.</p>
          </section>
        </article>
      </div>

      <aside className="principle-callout">
        <Info aria-hidden="true" />
        <div><strong>Reading these probabilities</strong><p>They estimate autopsy neuropathology in NACC participants who came to autopsy, not a clinical diagnosis. The next step evaluates whether they are reliable for this patient.</p></div>
      </aside>
      <StageActions currentCase={item} stage="predictions" nextLabel="Review reliability signals" />
    </div>
  );
}

export function LiveSafetyPage({ item, live }: { item: CaseView; live: LiveCase }) {
  const doc = live.document;
  const status = provisionalStatus(doc);
  return (
    <div className="page-content assessment-page safety-page">
      <LiveLead item={item} live={live} stage="safety" />
      <PageHeader
        eyebrow="Step 4 · Reliability signals"
        title="Prediction reliability (AD component)"
        description="Signals produced by the AD component for the team’s safety gate. The final TRUST / CAUTION / DEFER policy belongs to the Safety component."
      />
      <MriProgressBanner live={live} />

      <section className={`safety-result tone-${statusTone(status)} live-safety-result`}>
        <div className="safety-status-block">
          <p>Provisional status (AD component only)</p>
          <StatusBadge status={status} large />
          <span>Placeholder rule: any signal &lt; 0.40 → DEFER, any &lt; 0.70 → CAUTION, else TRUST. To be replaced by the Safety component (IT23147850).</span>
        </div>
      </section>

      <section className="content-section" aria-labelledby="signals-heading">
        <div className="section-heading"><div><p className="eyebrow">AD component</p><h2 id="signals-heading">Reliability signals</h2></div><p>Higher = more reliable. Hover a signal for its detail.</p></div>
        <div className="safety-signal-grid">
          {SIGNAL_ORDER.map((k) => {
            const s = doc.reliability_signals[k];
            if (s) {
              return <SafetySignalCard key={k} signal={{ key: k, label: SIGNAL_LABELS[k], score: s.score, level: signalLevel(s.score), description: s.detail + (s.experimental ? ' (experimental)' : '') }} />;
            }
            const why = k === 'clinicalHarmRisk' ? 'Provided by the Safety component' : k === 'modalityAgreement' ? 'Needs both clinical and MRI results' : 'Detector not available on this deployment';
            return (
              <article className="safety-signal live-signal-na" key={k}>
                <div className="signal-topline"><span>{SIGNAL_LABELS[k]}</span><strong>—</strong></div>
                <div className="signal-track" aria-hidden="true"><i style={{ width: 0 }} /></div>
                <div className="signal-footer"><span>N/A</span><small>{why}</small></div>
              </article>
            );
          })}
        </div>
      </section>
      <WarningList warnings={doc.warnings} />
      <StageActions currentCase={item} stage="safety" nextLabel="Generate report" />
    </div>
  );
}

export function LiveReportPage({ item, live }: { item: CaseView; live: LiveCase }) {
  const doc = live.document;
  const r = useMemo(() => reportSummary(live), [live]);
  const download = () => {
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${live.id}-neurosage-multilabel-v1.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const all = [...naccLabels(doc), ...mriLabels(doc)];

  return (
    <div className="page-content assessment-page report-page">
      <LiveLead item={item} live={live} stage="report" />
      <PageHeader
        eyebrow="Step 5 · Report hand-off"
        title="AD component summary"
        description="A deterministic template summary. The JSON download is the hand-off document for the Report / RAG component."
        aside={<ProvisionalBadge doc={doc} />}
      />
      <section className="report-document" aria-label="NeuroSage AD component summary">
        <header className="report-masthead">
          <div className="report-brand"><span><BrainCircuit aria-hidden="true" /></span><div><strong>NeuroSage</strong><small>AD co-pathology component · {doc.schema}</small></div></div>
          <dl><div><dt>Patient</dt><dd>{doc.patient_ref}</dd></div><div><dt>Case</dt><dd>{live.id}</dd></div><div><dt>Generated</dt><dd>{doc.generated_at.replace('T', ' ').replace('Z', ' UTC')}</dd></div></dl>
        </header>
        <section className="report-section"><header><UserRound aria-hidden="true" /><h2>Summary</h2></header><p className="report-lead">{r.patientSummary}</p></section>
        <section className="report-section">
          <header><Gauge aria-hidden="true" /><h2>Model findings</h2></header>
          <div className="report-findings">
            {all.map((l) => (
              <div key={l.key}>
                <span>{l.label}<small className="live-muted"> · {l.predicted ? 'above' : 'below'} threshold {pct(l.threshold)}</small></span>
                <strong>{pct(l.probability)}</strong>
                <div className="metric-track"><i style={{ width: `${l.probability * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </section>
        <div className="report-columns">
          <section className="report-section"><header><Microscope aria-hidden="true" /><h2>Top supporting features</h2></header>
            <ul className="report-list">{r.supportingEvidence.map((e) => <li key={e}><CheckCircle2 aria-hidden="true" />{e}</li>)}</ul>
          </section>
          <section className="report-section"><header><ShieldAlert aria-hidden="true" /><h2>Reliability caveats</h2></header>
            <ul className="report-list safety-list">{r.safetyConsiderations.map((c) => <li key={c}><TriangleAlert aria-hidden="true" />{c}</li>)}</ul>
          </section>
        </div>
        <section className="report-section"><header><Stethoscope aria-hidden="true" /><h2>Interpretation</h2></header><blockquote>{r.recommendation}</blockquote></section>
        <footer className="report-disclaimer"><Info aria-hidden="true" />{DISCLAIMER} Probabilities estimate autopsy neuropathology risk and are not a diagnosis. PD component not connected.</footer>
      </section>
      <div className="report-actions no-print">
        <Button variant="outline" size="lg" onClick={download}><Download aria-hidden="true" />Download JSON</Button>
        <Button variant="outline" size="lg" onClick={() => window.print()}><Printer aria-hidden="true" />Print summary</Button>
        <ModelCardDialog />
        <Button size="lg" className="ml-auto bg-[#1f65a8] hover:bg-[#174f86]" render={<Link href="/" />}><LayoutDashboard aria-hidden="true" />Back to dashboard</Button>
      </div>
      <StageActions currentCase={item} stage="report" />
    </div>
  );
}


export function LiveCaseLoading() {
  return (
    <div className="page-content error-page" aria-busy="true">
      <div className="error-illustration"><LoaderCircle className="animate-spin" aria-hidden="true" /></div>
      <p className="eyebrow">Loading live case</p>
    </div>
  );
}

// ------------------------------------------------------------------ model card
interface CardRow { label: string; auroc?: number; ci?: number[]; bacc?: number; ece?: number; threshold?: number }

export function ModelCardDialog() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || data || !isLiveEnabled) return;
    getModels().then(setData).catch((e: Error) => setError(e.message));
  }, [open, data]);

  const rows: CardRow[] = [];
  if (data) {
    const active = data.active_nacc_model as string;
    const reported = (data.reported_performance as Record<string, Record<string, { test_auroc: number; test_auroc_ci: number[]; test_bacc: number; test_ece: number }>>).RandomForest;
    const thr = (data.nacc_thresholds as Record<string, Record<string, number>>)[active] ?? {};
    for (const [k, v] of Object.entries(reported)) {
      rows.push({ label: k.replace('y_', ''), auroc: v.test_auroc, ci: v.test_auroc_ci, bacc: v.test_bacc, ece: v.test_ece, threshold: thr[k] });
    }
  }
  const stability = (data?.explanation_stability ?? {}) as Record<string, { spearman: number; jaccard_top10: number }>;
  const adni = (data?.adni ?? {}) as Record<string, { kind: string; arch?: string; threshold: number }>;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="lg" />}><BookOpenCheck aria-hidden="true" />About the model</DialogTrigger>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto p-6">
        <DialogHeader>
          <DialogTitle className="text-lg text-slate-900">AD co-pathology component · model card</DialogTitle>
          <DialogDescription>IT23174276 · J26-DS-306. {DISCLAIMER}</DialogDescription>
        </DialogHeader>
        {!isLiveEnabled && <p className="live-muted">The analysis service is not configured.</p>}
        {error && <p className="live-muted">Could not load the model card: {error}</p>}
        {isLiveEnabled && !data && !error && <p className="live-muted"><LoaderCircle className="inline size-4 animate-spin" aria-hidden="true" /> Loading…</p>}
        {data && (
          <div className="live-card">
            <p>Active clinical model: <strong>{String(data.active_nacc_model).toUpperCase()}</strong>. Thesis metrics are the Random Forest on the locked NACC test set (n = 1,057, bootstrap 95% CI).</p>
            <div className="table-surface live-scroll">
              <Table>
                <TableHeader><TableRow><TableHead>Label</TableHead><TableHead>AUROC [95% CI]</TableHead><TableHead>BACC</TableHead><TableHead>ECE</TableHead><TableHead>Threshold</TableHead><TableHead>SHAP stability</TableHead></TableRow></TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={r.label}>
                      <TableCell className="font-semibold">{r.label}</TableCell>
                      <TableCell>{r.auroc?.toFixed(3)} [{r.ci?.[0]?.toFixed(3)}–{r.ci?.[1]?.toFixed(3)}]</TableCell>
                      <TableCell>{r.bacc?.toFixed(3)}</TableCell>
                      <TableCell>{r.ece?.toFixed(3)}</TableCell>
                      <TableCell>{r.threshold?.toFixed(3) ?? '—'}</TableCell>
                      <TableCell>ρ {stability[`y_${r.label}`]?.spearman.toFixed(2)} · J {stability[`y_${r.label}`]?.jaccard_top10.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {Object.keys(adni).length > 0 && (
              <p>MRI models loaded: {Object.entries(adni).map(([k, v]) => `${k} (${v.kind}${v.arch ? `, ${v.arch}` : ''}, threshold ${v.threshold.toFixed(3)})`).join('; ')}. Clinical-AD fusion: test AUROC 0.953 [0.909–0.987]; CSF-biomarker AD (tabular): 0.759 [0.650–0.850].</p>
            )}
            <p className="live-caveat"><TriangleAlert aria-hidden="true" />{String(data.openset_caveat)}</p>
            <p><strong>Data sources:</strong> {(data.data_sources as string[]).join('; ')}.</p>
            <p><strong>Data use:</strong> {String(data.dua_notice)}</p>
          </div>
        )}
        <DialogFooter showCloseButton />
      </DialogContent>
    </Dialog>
  );
}
