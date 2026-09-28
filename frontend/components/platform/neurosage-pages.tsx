'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  Activity,
  ArrowDown,
  ArrowRight,
  Binary,
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Cpu,
  FileSearch,
  FileText,
  GitBranch,
  LayoutDashboard,
  OctagonAlert,
  ShieldCheck,
  TriangleAlert,
  UserRound,
  Workflow,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { AD_API_URL, isLiveEnabled } from '@/lib/ad/api';
import { toViewModel, useLiveCases } from '@/lib/ad/live-cases';
import {
  caseHref,
  type CaseView,
  type Modality,
  type SafetySignal,
} from '@/lib/assessment';
import { Principle, PageHeader, StatusBadge } from '@/components/platform/neurosage-ui';

function useCaseViews(): CaseView[] {
  const store = useLiveCases();
  return useMemo(
    () => Object.values(store).map(toViewModel).sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    [store],
  );
}

function StatStrip({ cases }: { cases: CaseView[] }) {
  const count = (status: CaseView['safety']['overallStatus']) => cases.filter((c) => c.safety.overallStatus === status).length;
  const stats = [
    { label: 'Assessed patients', value: cases.length, icon: UserRound, tone: 'clinical' },
    { label: 'TRUST', value: count('TRUST'), icon: ShieldCheck, tone: 'trust' },
    { label: 'CAUTION', value: count('CAUTION'), icon: TriangleAlert, tone: 'caution' },
    { label: 'DEFER', value: count('DEFER'), icon: OctagonAlert, tone: 'defer' },
  ];

  return (
    <section className="stats-grid" aria-label="Case overview">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div className="stat-item" key={stat.label}>
            <span className={`stat-icon tone-${stat.tone}`}><Icon aria-hidden="true" /></span>
            <span><strong>{stat.value}</strong><small>{stat.label}</small></span>
          </div>
        );
      })}
    </section>
  );
}

function CompactWorkflow() {
  const steps = [
    { label: 'Patient data', icon: UserRound },
    { label: 'Harmonize', icon: Binary },
    { label: 'Parallel AI', icon: GitBranch },
    { label: 'Safety gate', icon: ShieldCheck },
    { label: 'Clinical report', icon: FileText },
  ];

  return (
    <div className="compact-workflow" aria-label="NeuroSage workflow">
      {steps.map((step, index) => {
        const Icon = step.icon;
        return (
          <div className="compact-flow-segment" key={step.label}>
            <span><Icon aria-hidden="true" />{step.label}</span>
            {index < steps.length - 1 && <ArrowRight aria-hidden="true" />}
          </div>
        );
      })}
    </div>
  );
}

export function DashboardPage() {
  const cases = useCaseViews();

  return (
    <div className="page-content dashboard-page">
      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <p className="eyebrow">Explainable · Multi-label · Open-set aware</p>
          <h1 id="dashboard-title">Explainable &amp; Safety-Aware<br className="hidden sm:block" /> Clinical Prediction Platform</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-6 text-slate-600">
            Enter a patient and the trained AD co-pathology models, running on this computer, return calibrated
            probabilities, explanations and reliability signals.
          </p>
        </div>
        <Button size="lg" className="primary-route-button" render={<Link href="/assessment/new" />}>
          <ClipboardCheck aria-hidden="true" /> New assessment <ArrowRight aria-hidden="true" />
        </Button>
      </section>

      <CompactWorkflow />
      <StatStrip cases={cases} />

      <section className="content-section recent-cases" aria-labelledby="recent-heading">
        <div className="section-heading">
          <div><p className="eyebrow">This browser tab</p><h2 id="recent-heading">Assessed patients</h2></div>
          <span className="static-data-label">
            <Cpu aria-hidden="true" />
            {isLiveEnabled ? `Local models · ${AD_API_URL}` : 'Model service not configured'}
          </span>
        </div>
        {cases.length === 0 ? (
          <aside className="missing-data-note">
            <CircleAlert aria-hidden="true" />
            <p><strong>No assessments yet.</strong> Run a new assessment to see results from the trained models here.</p>
          </aside>
        ) : (
          <div className="table-surface">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Patient</TableHead>
                  <TableHead>Data status</TableHead>
                  {cases[0].adPredictions.map((p) => <TableHead key={p.label}>{p.label}</TableHead>)}
                  <TableHead className="text-right">Safety (provisional)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cases.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-semibold text-slate-800">
                      <Link href={caseHref(c.id, 'predictions')}>{c.patient.id} · {c.id}</Link>
                    </TableCell>
                    <TableCell>{c.dataStatus}</TableCell>
                    {c.adPredictions.map((p) => (
                      <TableCell key={p.label} className="tabular-nums">{Math.round(p.probability * 100)}%</TableCell>
                    ))}
                    <TableCell className="text-right"><StatusBadge status={c.safety.overallStatus} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>
    </div>
  );
}

function WorkflowNode({ icon: Icon, title, detail, accent }: { icon: typeof Activity; title: string; detail: string; accent?: string }) {
  return (
    <div className={`workflow-node ${accent ? `accent-${accent}` : ''}`}>
      <span><Icon aria-hidden="true" /></span>
      <div><strong>{title}</strong><small>{detail}</small></div>
    </div>
  );
}

export function WorkflowPage() {
  return (
    <div className="page-content workflow-page">
      <PageHeader
        eyebrow="Research workflow"
        title="How NeuroSage works"
        description="One integrated path connects multimodal data, independent disease models, safety evaluation, and evidence-grounded reporting."
        aside={<Button render={<Link href="/assessment/new" />} className="primary-route-button"><ClipboardCheck />Start assessment</Button>}
      />

      <figure className="workflow-visual">
        <Image
          src="/og.png"
          width="1672"
          height="941"
          alt="NeuroSage concept showing brain imaging data moving through parallel analysis toward a three-state safety gate"
        />
        <figcaption>Multimodal evidence is interpreted through an explicit prediction-safety layer.</figcaption>
      </figure>

      <section className="workflow-canvas" aria-label="Complete NeuroSage system workflow">
        <WorkflowNode icon={UserRound} title="Patient multimodal data" detail="MRI · Clinical · Biomarkers · Genetics · DaTSCAN" accent="blue" />
        <ArrowDown className="workflow-arrow" aria-hidden="true" />
        <WorkflowNode icon={Binary} title="Data harmonization" detail="Map heterogeneous sources into one representation" accent="blue" />
        <ArrowDown className="workflow-arrow" aria-hidden="true" />

        <div className="parallel-workflow">
          <div className="parallel-heading"><GitBranch aria-hidden="true" /><strong>Parallel AI models</strong><span>Independent analysis paths</span></div>
          <div className="parallel-models">
            <WorkflowNode icon={BrainCircuit} title="Alzheimer’s & co-pathology" detail="Multi-label disease probabilities + explanation" />
            <WorkflowNode icon={Activity} title="Parkinson’s disease" detail="PD and motor-risk probabilities + explanation" />
          </div>
          <div className="merge-label"><span />Combined predictions<span /></div>
        </div>

        <ArrowDown className="workflow-arrow" aria-hidden="true" />
        <WorkflowNode icon={ShieldCheck} title="Prediction safety gate" detail="Sufficiency · Familiarity · Certainty · Agreement · Explanation" accent="amber" />
        <div className="workflow-outcomes" aria-label="Safety outcomes">
          <StatusBadge status="TRUST" large />
          <StatusBadge status="CAUTION" large />
          <StatusBadge status="DEFER" large />
        </div>
        <ArrowDown className="workflow-arrow" aria-hidden="true" />
        <WorkflowNode icon={BookOpenCheck} title="LLM + RAG reporting framework" detail="Predictions + safety + explanations + retrieved evidence" accent="blue" />
        <ArrowDown className="workflow-arrow" aria-hidden="true" />
        <WorkflowNode icon={FileText} title="Clinician-friendly summary" detail="Structured interpretation with limitations and recommended action" accent="green" />
      </section>

      <Principle>
        Predictive performance alone is not enough. NeuroSage assesses whether each prediction is safe to rely on before reporting it.
      </Principle>
    </div>
  );
}

export function ModalityStatus({ modality }: { modality: Modality }) {
  const normalized = modality.status.toLowerCase().replace('_', '-');
  const labels: Record<Modality['status'], string> = {
    AVAILABLE: 'Available',
    MISSING: 'Missing',
    PARTIAL: 'Partial',
    NOT_APPLICABLE: 'Not applicable',
  };
  const Icon = modality.status === 'AVAILABLE' ? CheckCircle2 : modality.status === 'MISSING' ? CircleAlert : TriangleAlert;

  return <span className={`modality-status status-${normalized}`}><Icon aria-hidden="true" />{labels[modality.status]}</span>;
}

function signalTone(signal: SafetySignal): string {
  if (signal.key === 'clinicalHarmRisk') {
    return signal.level === 'HIGH' ? 'defer' : signal.level === 'MEDIUM' ? 'caution' : 'trust';
  }
  return signal.level === 'HIGH' ? 'trust' : signal.level === 'MEDIUM' ? 'caution' : 'defer';
}

export function SafetySignalCard({ signal }: { signal: SafetySignal }) {
  const tone = signalTone(signal);
  return (
    <article className={`safety-signal tone-${tone}`} title={signal.description}>
      <div className="signal-topline"><span>{signal.label}</span><strong>{signal.score.toFixed(2)}</strong></div>
      <div className="signal-track" aria-label={`${signal.label} ${signal.score.toFixed(2)} ${signal.level}`}><i style={{ width: `${signal.score * 100}%` }} /></div>
      <div className="signal-footer"><span>{signal.level}</span><small>{signal.description}</small></div>
    </article>
  );
}

export function InvalidCasePage() {
  return (
    <div className="page-content error-page">
      <div className="error-illustration"><FileSearch aria-hidden="true" /></div>
      <p className="eyebrow">Assessment unavailable</p>
      <h1>Case not found.</h1>
      <p>Assessments are kept only in the browser tab that ran them. Start a new assessment to run the models again.</p>
      <Button size="lg" className="primary-route-button" render={<Link href="/" />}><LayoutDashboard aria-hidden="true" />Return to dashboard</Button>
    </div>
  );
}

export function InvalidStagePage({ item }: { item: CaseView }) {
  return (
    <div className="page-content error-page">
      <div className="error-illustration"><Workflow aria-hidden="true" /></div>
      <p className="eyebrow">Unknown workflow stage</p>
      <h1>This assessment stage is not available.</h1>
      <p>Continue from the patient-data step for {item.patient.id}.</p>
      <Button size="lg" className="primary-route-button" render={<Link href={caseHref(item.id, 'patient')} />}><ArrowRight aria-hidden="true" />Open patient data</Button>
    </div>
  );
}
