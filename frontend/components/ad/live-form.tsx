'use client';

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  CircleAlert,
  ClipboardList,
  FlaskConical,
  LoaderCircle,
  Plus,
  RotateCcw,
  ScanLine,
  Sparkles,
  Trash2,
  UserRound,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { PageHeader } from '@/components/platform/neurosage-ui';
import { ResearchDisclaimer } from '@/components/ad/results';
import { COLD_START_MESSAGE, getFormSpec, listDemoMri, predictClinical } from '@/lib/ad/api';
import {
  symptomKeys,
  vascularKeys,
  type ClinicalRequest,
  type DemoMriCase,
  type FormField,
  type FormSpec,
  type MriFields,
  type SymptomKey,
  type VascularKey,
  type VisitInput,
} from '@/lib/ad/types';
import { addLiveCase, runMriDemo, runMriUpload } from '@/lib/ad/live-cases';

type Draft = Record<string, string>;

interface VisitDraft {
  uid: number;
  date: string;
  age: string;
  cogMode: 'mmse' | 'moca';
  cog: string;
  untestable: boolean;
  cdr_global: string;
  cdr_sum: string;
  gds: string;
  bmi: string;
  bp_systolic: string;
  symptoms: Draft;
  vascular: Draft;
}

let uidCounter = 0;
const emptyVisit = (): VisitDraft => ({
  uid: ++uidCounter, date: '', age: '', cogMode: 'mmse', cog: '', untestable: false, cdr_global: '', cdr_sum: '',
  gds: '', bmi: '', bp_systolic: '', symptoms: {}, vascular: {},
});

const optValue = (v: string | number | boolean | null | undefined) => (v === null || v === undefined ? '' : String(v));
const num = (s: string | undefined): number | null => (s == null || s.trim() === '' ? null : Number(s));
const tri = (s: string | undefined): boolean | null => (s === 'true' ? true : s === 'false' ? false : null);

const EXAMPLE = {
  patient: { id: 'P-EXAMPLE-001', sex: 'female', education_years: '14', hispanic: 'false', race: 'asian', apoe_e4_count: '1', family_history: 'true' } as Draft,
  visits: [
    { date: '2021-03-14', age: '72.2', cogMode: 'moca', cog: '24', cdr_global: '0.5', cdr_sum: '1.5', gds: '3', bmi: '24.1', bp_systolic: '138', symptoms: { rem_sleep_behaviour: 'true' }, vascular: { hypertension: 'active', stroke: 'absent' } },
    { date: '2022-03-20', age: '73.2', cogMode: 'mmse', cog: '25', cdr_global: '0.5', cdr_sum: '2.5', gds: '4', bmi: '23.8', bp_systolic: '140', symptoms: {}, vascular: { hypertension: 'active' } },
    { date: '2023-03-14', age: '74.2', cogMode: 'moca', cog: '21', cdr_global: '0.5', cdr_sum: '3', gds: '4', bmi: '24.1', bp_systolic: '138', symptoms: { visual_hallucinations: 'false', rem_sleep_behaviour: 'true' }, vascular: { hypertension: 'active', hypercholesterolaemia: 'remote', stroke: 'absent' } },
  ] as Array<Partial<VisitDraft>>,
};

// ------------------------------------------------------------------ field primitives
function FieldLabel({ field, htmlFor, highImpact }: { field: FormField; htmlFor: string; highImpact: boolean }) {
  return (
    <label htmlFor={htmlFor} className="live-label">
      <span>{field.label}{field.required && <span aria-hidden="true"> *</span>}</span>
      {field.unit && <small>{field.unit}</small>}
      {highImpact && <em className="live-impact">High impact</em>}
    </label>
  );
}

function SpecInput({
  field, id, value, onChange, highImpact, disabled,
}: {
  field: FormField; id: string; value: string; onChange: (v: string) => void; highImpact: boolean; disabled?: boolean;
}) {
  const describedBy = field.help ? `${id}-help` : undefined;
  let control: ReactNode;
  if (field.type === 'select' || field.type === 'tri' || field.type === 'vascular') {
    const hasNull = field.options?.some((o) => o.value === null);
    control = (
      <NativeSelect id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} aria-describedby={describedBy} className="w-full">
        {!hasNull && <NativeSelectOption value="">Unknown</NativeSelectOption>}
        {field.options?.map((o) => <NativeSelectOption key={optValue(o.value)} value={optValue(o.value)}>{o.label}</NativeSelectOption>)}
      </NativeSelect>
    );
  } else {
    control = (
      <Input
        id={id}
        type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
        inputMode={field.type === 'number' ? 'decimal' : undefined}
        min={field.min}
        max={field.max}
        step={field.step}
        required={field.required}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby={describedBy}
        maxLength={field.type === 'text' ? 64 : undefined}
      />
    );
  }
  return (
    <div className="live-field">
      <FieldLabel field={field} htmlFor={id} highImpact={highImpact} />
      {control}
      {field.help && <small id={describedBy} className="live-help">{field.help}</small>}
    </div>
  );
}

function Section({ icon: Icon, title, hint, children, action }: { icon: typeof UserRound; title: string; hint?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="live-form-section">
      <header>
        <span><Icon aria-hidden="true" /></span>
        <div><h2>{title}</h2>{hint && <p>{hint}</p>}</div>
        {action}
      </header>
      {children}
    </section>
  );
}

// ------------------------------------------------------------------ main form
export function AdLiveForm() {
  const router = useRouter();
  const [spec, setSpec] = useState<FormSpec | null>(null);
  const [specError, setSpecError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [patient, setPatient] = useState<Draft>({ id: '' });
  const [visits, setVisits] = useState<VisitDraft[]>([emptyVisit()]);
  const [csf, setCsf] = useState<Draft>({});
  const [mriMode, setMriMode] = useState<'none' | 'upload' | 'demo'>('none');
  const [mriFile, setMriFile] = useState<File | null>(null);
  const [mriAge, setMriAge] = useState('');
  const [demoCases, setDemoCases] = useState<DemoMriCase[]>([]);
  const [demoId, setDemoId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchSpec = () => {
    getFormSpec({ onSlow: () => setWaking(true) })
      .then((s) => { setSpec(s); setWaking(false); })
      .catch((e: Error) => { setSpecError(e.message); setWaking(false); });
    listDemoMri().then(setDemoCases).catch(() => setDemoCases([]));
  };
  useEffect(fetchSpec, []);
  const retrySpec = () => {
    setSpecError(null);
    setWaking(false);
    fetchSpec();
  };

  const highImpact = useMemo(() => new Set(spec?.high_impact ?? []), [spec]);
  const field = (group: FormField[] | undefined, key: string) => group?.find((f) => f.key === key);

  const setVisit = (uid: number, update: Partial<VisitDraft>) =>
    setVisits((vs) => vs.map((v) => (v.uid === uid ? { ...v, ...update } : v)));

  const loadExample = () => {
    setPatient(EXAMPLE.patient);
    setVisits(EXAMPLE.visits.map((v) => ({ ...emptyVisit(), ...v } as VisitDraft)));
    setCsf({});
  };

  function buildRequest(): ClinicalRequest {
    const v: VisitInput[] = visits.map((d) => {
      const cog = d.untestable ? null : num(d.cog);
      return {
        date: d.date,
        age: Number(d.age),
        mmse: d.cogMode === 'mmse' ? cog : null,
        moca: d.cogMode === 'moca' ? cog : null,
        cognition_untestable: d.untestable,
        cdr_global: num(d.cdr_global),
        cdr_sum: num(d.cdr_sum),
        gds: num(d.gds),
        bmi: num(d.bmi),
        bp_systolic: num(d.bp_systolic),
        symptoms: Object.fromEntries(symptomKeys.map((k) => [k, tri(d.symptoms[k])])) as Record<SymptomKey, boolean | null>,
        vascular: Object.fromEntries(vascularKeys.map((k) => [k, (d.vascular[k] || null) as VisitInput['vascular'][VascularKey]])) as VisitInput['vascular'],
      };
    });
    const csfVals = { abeta42: num(csf.abeta42), ptau181: num(csf.ptau181), ttau: num(csf.ttau), assay: csf.assay?.trim() || null };
    const hasCsf = csfVals.abeta42 != null || csfVals.ptau181 != null || csfVals.ttau != null;
    return {
      patient: {
        id: patient.id?.trim() || 'anonymous',
        sex: (patient.sex || null) as ClinicalRequest['patient']['sex'],
        education_years: num(patient.education_years),
        hispanic: tri(patient.hispanic),
        race: (patient.race || null) as ClinicalRequest['patient']['race'],
        apoe_e4_count: num(patient.apoe_e4_count) as 0 | 1 | 2 | null,
        family_history: tri(patient.family_history),
      },
      visits: v,
      csf: hasCsf ? csfVals : null,
      options: { explain: true, model: 'auto' },
    };
  }

  function clientErrors(): string | null {
    if (!visits.length) return 'Add at least one visit.';
    for (const [i, v] of visits.entries()) {
      if (!v.date) return `Visit ${i + 1}: the date is required.`;
      if (!v.age) return `Visit ${i + 1}: age is required.`;
    }
    const dates = visits.map((v) => v.date);
    if (new Set(dates).size !== dates.length) return 'Each visit needs a different date.';
    if (mriMode === 'upload' && !mriFile) return 'Choose a T1 scan to upload, or switch MRI off.';
    if (mriMode === 'demo' && !demoId) return 'Choose a demo MRI case, or switch MRI off.';
    return null;
  }

  async function submit(e: { preventDefault(): void }) {
    e.preventDefault();
    const problem = clientErrors();
    if (problem) { setError(problem); return; }
    setError(null);
    setSubmitting(true);
    setWaking(false);
    const req = buildRequest();
    const last = [...req.visits].sort((a, b) => a.date.localeCompare(b.date)).at(-1)!;
    const mriFields: MriFields = {
      age_at_scan: num(mriAge) ?? last.age,
      sex: req.patient.sex,
      education_years: req.patient.education_years,
      apoe_e4_count: req.patient.apoe_e4_count,
    };
    try {
      const doc = await predictClinical(req, { onSlow: () => setWaking(true) });
      const live = addLiveCase(req, doc, mriMode === 'none' ? undefined : mriFields);
      if (mriMode === 'upload' && mriFile) void runMriUpload(live.id, mriFile, mriFields);
      if (mriMode === 'demo' && demoId) void runMriDemo(live.id, demoId, null);
      router.push(`/assessment/${live.id}/patient`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The assessment failed.');
      setSubmitting(false);
      setWaking(false);
    }
  }

  if (!spec) {
    return (
      <div className="page-content">
        <PageHeader eyebrow="Live assessment" title="AD co-pathology assessment" description="Loading the form from the analysis service." />
        {specError ? (
          <aside className="live-banner tone-defer" role="alert">
            <CircleAlert aria-hidden="true" />
            <div><p><strong>Could not load the form.</strong> {specError}</p><Button variant="outline" size="sm" onClick={retrySpec}><RotateCcw aria-hidden="true" />Try again</Button></div>
          </aside>
        ) : (
          <aside className="live-banner" aria-live="polite"><LoaderCircle className="animate-spin" aria-hidden="true" /><p>{waking ? COLD_START_MESSAGE : 'Loading…'}</p></aside>
        )}
      </div>
    );
  }

  const cogField = (mode: 'mmse' | 'moca') => field(spec.visit, mode)!;

  return (
    <div className="page-content live-form-page">
      <PageHeader
        eyebrow="Live assessment · AD component"
        title="AD co-pathology assessment"
        description="Enter what you know. Unknown values can stay empty: the model imputes them and the data-sufficiency signal drops."
        aside={<Button type="button" variant="outline" onClick={loadExample}><Sparkles aria-hidden="true" />Load example patient</Button>}
      />
      <ResearchDisclaimer />

      <form onSubmit={submit} noValidate>
        <Section icon={UserRound} title="Patient" hint="Entered once; copied onto every visit.">
          <div className="live-grid">
            {spec.patient.map((f) => (
              <SpecInput key={f.key} field={f} id={`p-${f.key}`} value={patient[f.key] ?? ''} highImpact={highImpact.has(f.key) || !!f.high_impact}
                onChange={(val) => setPatient((p) => ({ ...p, [f.key]: val }))} />
            ))}
          </div>
        </Section>

        <Section
          icon={ClipboardList}
          title="Visits"
          hint={spec.hints.visits}
          action={<Button type="button" variant="outline" size="sm" onClick={() => setVisits((vs) => [...vs, emptyVisit()])}><Plus aria-hidden="true" />Add visit</Button>}
        >
          <ol className="live-visits">
            {visits.map((v, i) => {
              const cf = cogField(v.cogMode);
              const idp = `v${v.uid}`;
              return (
                <li key={v.uid} className="live-visit">
                  <header>
                    <strong>Visit {i + 1}</strong>
                    {visits.length > 1 && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => setVisits((vs) => vs.filter((x) => x.uid !== v.uid))} aria-label={`Remove visit ${i + 1}`}>
                        <Trash2 aria-hidden="true" />Remove
                      </Button>
                    )}
                  </header>
                  <div className="live-grid">
                    {(['date', 'age'] as const).map((k) => (
                      <SpecInput key={k} field={field(spec.visit, k)!} id={`${idp}-${k}`} value={v[k]} highImpact={highImpact.has(k)} onChange={(val) => setVisit(v.uid, { [k]: val })} />
                    ))}
                    <div className="live-field">
                      <div className="live-label">
                        <span id={`${idp}-cog-label`}>Cognition</span>
                        <small>/30</small>
                        <em className="live-impact">High impact</em>
                      </div>
                      <div className="live-cog">
                        <fieldset className="live-toggle" aria-labelledby={`${idp}-cog-label`}>
                          {(['mmse', 'moca'] as const).map((m) => (
                            <button key={m} type="button" aria-pressed={v.cogMode === m} className={v.cogMode === m ? 'is-active' : ''}
                              disabled={v.untestable} onClick={() => setVisit(v.uid, { cogMode: m })}>{m === 'mmse' ? 'MMSE' : 'MoCA'}</button>
                          ))}
                        </fieldset>
                        <Input id={`${idp}-cog`} type="number" inputMode="decimal" min={0} max={30} step={1} value={v.untestable ? '' : v.cog}
                          disabled={v.untestable} onChange={(e) => setVisit(v.uid, { cog: e.target.value })} aria-label={`${v.cogMode === 'mmse' ? 'MMSE' : 'MoCA'} score, 0 to 30`} />
                      </div>
                      <label className="live-check">
                        <input type="checkbox" checked={v.untestable} onChange={(e) => setVisit(v.uid, { untestable: e.target.checked })} />
                        Cognition untestable
                      </label>
                      <small className="live-help">{cf.help}</small>
                    </div>
                    {(['cdr_global', 'cdr_sum', 'gds', 'bmi', 'bp_systolic'] as const).map((k) => (
                      <SpecInput key={k} field={field(spec.visit, k)!} id={`${idp}-${k}`} value={v[k]} highImpact={highImpact.has(k)} onChange={(val) => setVisit(v.uid, { [k]: val })} />
                    ))}
                  </div>
                  <details className="live-details">
                    <summary>Symptoms &amp; vascular history <small>({Object.values(v.symptoms).filter(Boolean).length + Object.values(v.vascular).filter(Boolean).length} answered)</small></summary>
                    <div className="live-grid">
                      {spec.symptoms.map((f) => (
                        <SpecInput key={f.key} field={f} id={`${idp}-s-${f.key}`} value={v.symptoms[f.key] ?? ''} highImpact={highImpact.has(f.key) || !!f.high_impact}
                          onChange={(val) => setVisit(v.uid, { symptoms: { ...v.symptoms, [f.key]: val } })} />
                      ))}
                    </div>
                    <div className="live-grid">
                      {spec.vascular.map((f) => (
                        <SpecInput key={f.key} field={f} id={`${idp}-x-${f.key}`} value={v.vascular[f.key] ?? ''} highImpact={highImpact.has(f.key) || !!f.high_impact}
                          onChange={(val) => setVisit(v.uid, { vascular: { ...v.vascular, [f.key]: val } })} />
                      ))}
                    </div>
                  </details>
                </li>
              );
            })}
          </ol>
        </Section>

        <details className="live-form-section live-collapsible">
          <summary><FlaskConical aria-hidden="true" /><span><strong>CSF biomarkers</strong> <small>optional · not harmonised across assays</small></span></summary>
          <div className="live-grid">
            {spec.csf.map((f) => (
              <SpecInput key={f.key} field={f} id={`csf-${f.key}`} value={csf[f.key] ?? ''} highImpact={false} onChange={(val) => setCsf((c) => ({ ...c, [f.key]: val }))} />
            ))}
          </div>
        </details>

        <Section icon={ScanLine} title="MRI (optional)" hint="A T1 MPRAGE adds the ADNI clinical-AD and biomarker-AD models. Scans are deleted after analysis.">
          <fieldset className="live-toggle is-wide" aria-label="MRI input">
            {([['none', 'No MRI'], ['upload', 'Upload T1'], ['demo', `Demo MRI${demoCases.length ? '' : ' (none available)'}`]] as const).map(([k, label]) => (
              <button key={k} type="button" aria-pressed={mriMode === k} className={mriMode === k ? 'is-active' : ''}
                disabled={k === 'demo' && !demoCases.length} onClick={() => setMriMode(k)}>{label}</button>
            ))}
          </fieldset>
          {mriMode === 'upload' && (
            <div className="live-grid">
              <div className="live-field">
                <label htmlFor="mri-file" className="live-label"><span>T1 MPRAGE</span><small>.nii / .nii.gz / DICOM .zip</small></label>
                <input ref={fileRef} id="mri-file" type="file" accept=".nii,.gz,.zip" className="live-file" onChange={(e) => setMriFile(e.target.files?.[0] ?? null)} />
                <small className="live-help">Preprocessing takes about 2–4 minutes; progress appears on the results pages.</small>
              </div>
            </div>
          )}
          {mriMode === 'demo' && (
            <div className="live-grid">
              <div className="live-field">
                <label htmlFor="mri-demo" className="live-label"><span>Preprocessed test scan</span></label>
                <NativeSelect id="mri-demo" value={demoId} onChange={(e) => setDemoId(e.target.value)} className="w-full">
                  <NativeSelectOption value="">Choose…</NativeSelectOption>
                  {demoCases.map((d) => <NativeSelectOption key={d.id} value={d.id}>{d.description}</NativeSelectOption>)}
                </NativeSelect>
                <small className="live-help">Demo volumes use their own stored age, sex, education and APOE.</small>
              </div>
            </div>
          )}
          {mriMode === 'upload' && (
            <div className="live-grid">
              <SpecInput field={field(spec.mri, 'age_at_scan')!} id="mri-age" value={mriAge} highImpact={false} onChange={setMriAge} />
              <p className="live-help live-span">Sex, education and APOE are taken from the patient section. Age at scan defaults to the age at the last visit.</p>
            </div>
          )}
        </Section>

        {error && <aside className="live-banner tone-defer" role="alert"><CircleAlert aria-hidden="true" /><p>{error}</p></aside>}
        {submitting && <aside className="live-banner" aria-live="polite"><LoaderCircle className="animate-spin" aria-hidden="true" /><p>{waking ? COLD_START_MESSAGE : 'Running the clinical model and explanations…'}</p></aside>}

        <footer className="live-submit">
          <p>Inputs are sent to the AD analysis service for this request only and are not stored.</p>
          <Button type="submit" size="lg" className="h-10 bg-[#1f65a8] px-4 hover:bg-[#174f86]" disabled={submitting}>
            {submitting ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}Run assessment<ArrowRight aria-hidden="true" />
          </Button>
        </footer>
      </form>
    </div>
  );
}
