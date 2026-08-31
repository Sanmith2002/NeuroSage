'use client';

import type { CSSProperties } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  Activity,
  ArrowDown,
  ArrowRight,
  Binary,
  BookOpenCheck,
  BrainCircuit,
  Check,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Database,
  Dna,
  Download,
  FileCheck2,
  FileSearch,
  FileText,
  FlaskConical,
  Gauge,
  GitBranch,
  Info,
  LayoutDashboard,
  Microscope,
  OctagonAlert,
  Printer,
  ScanLine,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  TableProperties,
  TriangleAlert,
  UserRound,
  Workflow,
} from 'lucide-react';

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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from '@/components/ui/toast';
import {
  caseList,
  dashboardRecentCases,
  type AssessmentStage,
  type DemoCase,
  type Modality,
  type SafetySignal,
} from '@/lib/research';
import {
  AssessmentStepper,
  DemoPrinciple,
  FeatureImportance,
  PageHeader,
  ProbabilityBars,
  ProcessingBanner,
  ScenarioCard,
  StageActions,
  StatusBadge,
  statusTone,
} from '@/components/neurosage-ui';

const harmonizationSteps = [
  'Mapping source features...',
  'Standardizing modality inputs...',
  'Preparing unified patient representation...',
];

const analysisSteps = [
  'Running Alzheimer’s and co-pathology analysis...',
  'Running Parkinson’s disease analysis in parallel...',
  'Generating feature-level explanations...',
];

const safetySteps = [
  'Checking data sufficiency...',
  'Evaluating distribution conformity...',
  'Estimating prediction certainty...',
  'Checking modality agreement...',
  'Assessing domain familiarity...',
  'Validating explanation reliability...',
];

const modalityIcons: Record<string, typeof ScanLine> = {
  MRI: ScanLine,
  'Clinical data': ClipboardCheck,
  Biomarkers: FlaskConical,
  'Genetic data': Dna,
  DaTSCAN: Activity,
};

function StatStrip() {
  const stats = [
    { label: 'Patient cases', value: '24', icon: UserRound, tone: 'clinical' },
    { label: 'TRUST', value: '17', icon: ShieldCheck, tone: 'trust' },
    { label: 'CAUTION', value: '5', icon: TriangleAlert, tone: 'caution' },
    { label: 'DEFER', value: '2', icon: OctagonAlert, tone: 'defer' },
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
  return (
    <div className="page-content dashboard-page">
      <section className="dashboard-intro" aria-labelledby="dashboard-title">
        <div>
          <p className="eyebrow">Explainable · Multi-label · Open-set aware</p>
          <h1 id="dashboard-title">Explainable &amp; Safety-Aware<br className="hidden sm:block" /> Clinical Prediction Platform</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-6 text-slate-600">
            Follow one multimodal patient through harmonization, parallel disease analysis,
            a prediction safety gate, and a clinician-friendly report.
          </p>
        </div>
        <Button size="lg" className="primary-route-button" render={<Link href="/assessment/new" />}>
          <ClipboardCheck aria-hidden="true" /> Start demo assessment <ArrowRight aria-hidden="true" />
        </Button>
      </section>

      <CompactWorkflow />
      <StatStrip />

      <section className="content-section" aria-labelledby="scenarios-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Predefined patients</p><h2 id="scenarios-heading">Choose a demo scenario</h2></div>
          <p>Each patient demonstrates a different safety-gate outcome.</p>
        </div>
        <div className="scenario-grid">
          {caseList.map((item) => <ScenarioCard item={item} key={item.id} />)}
        </div>
      </section>

      <section className="content-section recent-cases" aria-labelledby="recent-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Completed examples</p><h2 id="recent-heading">Recent cases</h2></div>
          <span className="static-data-label"><Database aria-hidden="true" />Static demonstration data</span>
        </div>
        <div className="table-surface">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Patient</TableHead>
                <TableHead>Data status</TableHead>
                <TableHead>AD analysis</TableHead>
                <TableHead>PD analysis</TableHead>
                <TableHead className="text-right">Safety</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dashboardRecentCases.map((row) => (
                <TableRow key={row.patient}>
                  <TableCell className="font-semibold text-slate-800">{row.patient}</TableCell>
                  <TableCell>{row.dataStatus}</TableCell>
                  <TableCell><span className="complete-label"><Check aria-hidden="true" />{row.adStatus}</span></TableCell>
                  <TableCell><span className="complete-label"><Check aria-hidden="true" />{row.pdStatus}</span></TableCell>
                  <TableCell className="text-right"><StatusBadge status={row.safetyStatus} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}

export function NewAssessmentPage() {
  return (
    <div className="page-content">
      <PageHeader
        eyebrow="New assessment"
        title="Select a predefined patient"
        description="Start instantly with a complete mock scenario. No typing, uploading, or external service is required."
        aside={<span className="prototype-chip"><Sparkles aria-hidden="true" />Presentation-ready cases</span>}
      />

      <DemoPrinciple>
        Compare the model probability with its reliability signals. A confident output can still require caution or deferral.
      </DemoPrinciple>

      <div className="assessment-picker-grid">
        {caseList.map((item) => (
          <div className="assessment-choice" key={item.id}>
            <ScenarioCard item={item} compact />
            <dl>
              <div><dt>Patient</dt><dd>{item.patient.id}</dd></div>
              <div><dt>Data</dt><dd>{item.dataStatus}</dd></div>
              <div><dt>Reliability</dt><dd>{item.safety.reliabilityScore.toFixed(2)}</dd></div>
            </dl>
            <p className="demo-point"><Info aria-hidden="true" />{item.demoPoint}</p>
          </div>
        ))}
      </div>
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

      <DemoPrinciple>
        Predictive performance alone is not enough. NeuroSage assesses whether each prediction is safe to rely on before reporting it.
      </DemoPrinciple>
    </div>
  );
}

function CaseLead({ item, stage }: { item: DemoCase; stage: AssessmentStage }) {
  return (
    <>
      <AssessmentStepper currentCase={item} stage={stage} />
      <div className={`case-lead tone-${statusTone(item.safety.overallStatus)}`}>
        <div><span>{item.shortLabel}</span><strong>{item.title}</strong><small>{item.demoPoint}</small></div>
        <StatusBadge status={item.safety.overallStatus} />
      </div>
    </>
  );
}

function ModalityStatus({ modality }: { modality: Modality }) {
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

export function PatientPage({ item }: { item: DemoCase }) {
  return (
    <div className="page-content assessment-page">
      <CaseLead item={item} stage="patient" />
      <PageHeader
        eyebrow="Step 1 · Patient input"
        title="Patient assessment"
        description="Review the multimodal information entering the NeuroSage research pipeline."
        aside={<span className="patient-id"><UserRound aria-hidden="true" />{item.patient.id}</span>}
      />

      <section className="patient-summary-band" aria-labelledby="patient-details-heading">
        <div><p className="eyebrow">Patient information</p><h2 id="patient-details-heading">{item.patient.id}</h2><span>{item.patient.cohort}</span></div>
        <dl>
          <div><dt>Age</dt><dd>{item.patient.age}</dd></div>
          <div><dt>Sex</dt><dd>{item.patient.sex}</dd></div>
          <div><dt>Education</dt><dd>{item.patient.educationYears} years</dd></div>
          <div><dt>Data status</dt><dd>{item.dataStatus}</dd></div>
        </dl>
      </section>

      <section className="content-section" aria-labelledby="modalities-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Multimodal input</p><h2 id="modalities-heading">Available patient data</h2></div>
          <p>Missing or partial inputs remain visible throughout the workflow.</p>
        </div>
        <div className="modality-grid">
          {item.modalities.map((modality) => {
            const Icon = modalityIcons[modality.name] ?? TableProperties;
            return (
              <article className={`modality-card modality-${modality.status.toLowerCase()}`} key={modality.name}>
                <div className="modality-heading">
                  <span className="modality-icon"><Icon aria-hidden="true" /></span>
                  <div><h3>{modality.name}</h3><p>{modality.summary}</p></div>
                  <ModalityStatus modality={modality} />
                </div>
                <ul>{modality.details.map((detail) => <li key={detail}><Check aria-hidden="true" />{detail}</li>)}</ul>
              </article>
            );
          })}
        </div>
      </section>

      <aside className="missing-data-note"><Info aria-hidden="true" /><p><strong>Prototype behavior</strong> No file upload is required. NeuroSage carries the shown modality state into the predefined safety assessment.</p></aside>
      <StageActions currentCase={item} stage="patient" nextLabel="Prepare data" />
    </div>
  );
}

export function HarmonizationPage({ item }: { item: DemoCase }) {
  return (
    <div className="page-content assessment-page">
      <CaseLead item={item} stage="harmonization" />
      <PageHeader
        eyebrow="Step 2 · Standardization"
        title="Data harmonization"
        description="Map heterogeneous research variables into one shared representation while retaining disease-specific information."
      />

      <ProcessingBanner steps={harmonizationSteps} completeLabel="Data harmonization completed." />

      <section className="harmonization-flow" aria-label="Data harmonization stages">
        {[
          { label: 'Source datasets', detail: 'ADNI · PPMI', icon: Database },
          { label: 'Feature mapping', detail: 'Names + formats', icon: Workflow },
          { label: 'Standard representation', detail: 'Shared schema', icon: Binary },
          { label: 'Ready for models', detail: 'Quality state kept', icon: CheckCircle2 },
        ].map((step, index, list) => {
          const Icon = step.icon;
          return (
            <div className="harmonization-segment" key={step.label}>
              <div><span><Icon aria-hidden="true" /></span><strong>{step.label}</strong><small>{step.detail}</small></div>
              {index < list.length - 1 && <ArrowRight aria-hidden="true" />}
            </div>
          );
        })}
      </section>

      <div className="two-column-content harmonization-content">
        <section aria-labelledby="mapping-heading">
          <div className="section-heading compact"><div><p className="eyebrow">Mapped variables</p><h2 id="mapping-heading">Feature mapping</h2></div></div>
          <div className="table-surface">
            <Table>
              <TableHeader><TableRow><TableHead>Original feature</TableHead><TableHead>Source</TableHead><TableHead>Standard feature</TableHead><TableHead>Value</TableHead></TableRow></TableHeader>
              <TableBody>
                {item.harmonizedFeatures.map((row) => (
                  <TableRow key={`${row.source}-${row.originalFeature}`}>
                    <TableCell className="font-mono text-xs text-slate-700">{row.originalFeature}</TableCell>
                    <TableCell><span className="source-badge">{row.source}</span></TableCell>
                    <TableCell className="font-semibold text-slate-800">{row.standardFeature}</TableCell>
                    <TableCell>{row.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>

        <section aria-labelledby="readiness-heading">
          <div className="section-heading compact"><div><p className="eyebrow">Quality-aware output</p><h2 id="readiness-heading">Data readiness</h2></div></div>
          <div className="readiness-list">
            {item.modalities.map((modality) => (
              <div key={modality.name}>
                <span>{modality.name}<small>{modality.summary}</small></span>
                {modality.status === 'AVAILABLE' ? (
                  <span className="readiness-ok"><CheckCircle2 aria-hidden="true" />Standardized</span>
                ) : (
                  <ModalityStatus modality={modality} />
                )}
              </div>
            ))}
          </div>
        </section>
      </div>

      <DemoPrinciple>
        Harmonization standardizes the input representation without inventing missing data or hiding quality limitations.
      </DemoPrinciple>
      <StageActions currentCase={item} stage="harmonization" nextLabel="Continue to AI analysis" />
    </div>
  );
}

function ModelPanel({
  type,
  title,
  subtitle,
  predictions,
  features,
}: {
  type: 'ad' | 'pd';
  title: string;
  subtitle: string;
  predictions: DemoCase['adPredictions'];
  features: DemoCase['adFeatures'];
}) {
  const Icon = type === 'ad' ? BrainCircuit : Activity;
  return (
    <article className={`model-panel model-${type}`}>
      <header className="model-header">
        <span><Icon aria-hidden="true" /></span>
        <div><p>{type === 'ad' ? 'Component 1' : 'Component 2'}</p><h2>{title}</h2><small>{subtitle}</small></div>
      </header>
      <section><h3>Prediction results</h3><ProbabilityBars predictions={predictions} /></section>
      <section className="explanation-section"><h3>Prediction explanation</h3><p>Mock feature contribution · no live SHAP computation</p><FeatureImportance features={features} /></section>
    </article>
  );
}

export function PredictionsPage({ item }: { item: DemoCase }) {
  const isOOD = item.id === 'CASE-C';
  return (
    <div className="page-content assessment-page predictions-page">
      <CaseLead item={item} stage="predictions" />
      <PageHeader
        eyebrow="Step 3 · Parallel model inference"
        title="Disease analysis"
        description="Two independent components analyze the same harmonized patient representation at the same time."
      />
      <ProcessingBanner steps={analysisSteps} completeLabel="Parallel disease analysis complete." />

      <section className="parallel-indicator" aria-label="Parallel disease analysis structure">
        <span><Database aria-hidden="true" />Harmonized patient data</span>
        <div className="parallel-lines"><i /><GitBranch aria-hidden="true" /><i /></div>
        <strong>Parallel disease analysis</strong>
        <small>Neither model depends on the other</small>
      </section>

      <div className="model-grid">
        <ModelPanel type="ad" title="Alzheimer’s & co-pathology" subtitle="Multi-label neurodegenerative pathology analysis" predictions={item.adPredictions} features={item.adFeatures} />
        <ModelPanel type="pd" title="Parkinson’s disease" subtitle="Disease likelihood and motor impairment analysis" predictions={item.pdPredictions} features={item.pdFeatures} />
      </div>

      <div className="combined-results"><span /><div><CheckCircle2 aria-hidden="true" /><strong>Combined prediction set ready</strong><small>Both outputs now move to the independent safety gate.</small></div><span /></div>

      {isOOD ? (
        <aside className="ood-contrast">
          <div><span>Headline probability</span><strong>91%</strong><small>Alzheimer’s disease</small></div>
          <ArrowRight aria-hidden="true" />
          <div><span>Next question</span><strong>Is it safe?</strong><small>Probability alone cannot answer this.</small></div>
        </aside>
      ) : (
        <DemoPrinciple>The probability bars show what the models predict. The next stage decides whether those predictions are reliable enough to use.</DemoPrinciple>
      )}

      <StageActions currentCase={item} stage="predictions" nextLabel="Run safety assessment" />
    </div>
  );
}

function signalTone(signal: SafetySignal): string {
  if (signal.key === 'clinicalHarmRisk') {
    return signal.level === 'HIGH' ? 'defer' : signal.level === 'MEDIUM' ? 'caution' : 'trust';
  }
  return signal.level === 'HIGH' ? 'trust' : signal.level === 'MEDIUM' ? 'caution' : 'defer';
}

function SafetySignalCard({ signal }: { signal: SafetySignal }) {
  const tone = signalTone(signal);
  return (
    <article className={`safety-signal tone-${tone}`} title={signal.description}>
      <div className="signal-topline"><span>{signal.label}</span><strong>{signal.score.toFixed(2)}</strong></div>
      <div className="signal-track" aria-label={`${signal.label} ${signal.score.toFixed(2)} ${signal.level}`}><i style={{ width: `${signal.score * 100}%` }} /></div>
      <div className="signal-footer"><span>{signal.level}</span><small>{signal.description}</small></div>
    </article>
  );
}

export function SafetyPage({ item }: { item: DemoCase }) {
  const { safety } = item;
  const predictions = [...item.adPredictions, ...item.pdPredictions];
  const gaugeStyle = { '--gauge-value': `${safety.reliabilityScore * 360}deg` } as CSSProperties;

  return (
    <div className="page-content assessment-page safety-page">
      <CaseLead item={item} stage="safety" />
      <PageHeader
        eyebrow="Step 4 · Prediction safety gate"
        title="Prediction safety assessment"
        description="Evaluate whether the combined predictions are reliable enough to trust, use cautiously, or defer."
      />
      <ProcessingBanner steps={safetySteps} completeLabel="Safety assessment complete." />

      <section className={`safety-result tone-${statusTone(safety.overallStatus)}`}>
        <div className="safety-status-block">
          <p>Overall safety decision</p>
          <StatusBadge status={safety.overallStatus} large />
          <span>{safety.overallStatus === 'TRUST' ? 'Evidence is sufficiently reliable for standard interpretation.' : safety.overallStatus === 'CAUTION' ? 'Review identified limitations before relying on the result.' : 'Do not rely on the prediction without additional assessment.'}</span>
        </div>
        <div
          className="reliability-gauge"
          style={gaugeStyle}
          aria-label={`Reliability score ${safety.reliabilityScore.toFixed(2)}`}
        >
          <div><strong>{safety.reliabilityScore.toFixed(2)}</strong><span>Reliability</span></div>
        </div>
        <div className="safety-principle">
          <ShieldAlert aria-hidden="true" />
          <p><strong>High probability does not automatically mean safe to trust.</strong> NeuroSage evaluates the conditions around the prediction, not only its score.</p>
        </div>
      </section>

      {item.id === 'CASE-C' && (
        <section className="critical-contrast" aria-label="Case C safety contrast">
          <div><span>Alzheimer’s probability</span><strong>91%</strong><small>Model output is high</small></div>
          <div className="critical-divider"><ArrowRight aria-hidden="true" /><span>Safety gate</span></div>
          <div><span>Prediction reliability</span><strong>0.38</strong><small>Distribution + domain are unfamiliar</small></div>
          <StatusBadge status="DEFER" large />
        </section>
      )}

      <section className="content-section" aria-labelledby="signals-heading">
        <div className="section-heading"><div><p className="eyebrow">Component 3</p><h2 id="signals-heading">Safety signals</h2></div><p>Hover any signal to review what it measures.</p></div>
        <div className="safety-signal-grid">{safety.signals.map((signal) => <SafetySignalCard signal={signal} key={signal.key} />)}</div>
      </section>

      <div className="safety-detail-grid">
        <section className="reason-section" aria-labelledby="reason-heading">
          <div className="section-heading compact"><div><p className="eyebrow">Decision rationale</p><h2 id="reason-heading">Why was {safety.overallStatus} assigned?</h2></div></div>
          <div className="reason-list">
            {safety.reasons.map((reason) => <div key={reason}><CircleAlert aria-hidden="true" /><p>{reason}</p></div>)}
          </div>
        </section>

        <section aria-labelledby="label-safety-heading">
          <div className="section-heading compact"><div><p className="eyebrow">Per-output decision</p><h2 id="label-safety-heading">Label-level safety</h2></div></div>
          <div className="table-surface label-safety-table">
            <Table>
              <TableHeader><TableRow><TableHead>Prediction</TableHead><TableHead>Probability</TableHead><TableHead className="text-right">Safety</TableHead></TableRow></TableHeader>
              <TableBody>{predictions.map((prediction) => (
                <TableRow key={prediction.label}>
                  <TableCell className="font-medium text-slate-800">{prediction.label}</TableCell>
                  <TableCell className="font-semibold tabular-nums">{Math.round(prediction.probability * 100)}%</TableCell>
                  <TableCell className="text-right"><StatusBadge status={prediction.safetyStatus} /></TableCell>
                </TableRow>
              ))}</TableBody>
            </Table>
          </div>
        </section>
      </div>

      <aside className={`recommendation-callout tone-${statusTone(safety.overallStatus)}`}>
        <span><Stethoscope aria-hidden="true" /></span>
        <div><p>Recommended action</p><strong>{safety.recommendedAction}</strong></div>
      </aside>
      <StageActions currentCase={item} stage="safety" nextLabel="Generate clinical report" />
    </div>
  );
}

function ReportSection({ icon: Icon, title, children }: { icon: typeof Activity; title: string; children: React.ReactNode }) {
  return (
    <section className="report-section">
      <header><Icon aria-hidden="true" /><h2>{title}</h2></header>
      {children}
    </section>
  );
}

export function ReportPage({ item }: { item: DemoCase }) {
  const predictions = [...item.adPredictions, ...item.pdPredictions];
  const exportReport = () => toast.add({
    title: 'Prototype report prepared',
    description: 'The mock export was generated successfully. No patient data was stored.',
    type: 'success',
  });

  return (
    <div className="page-content assessment-page report-page">
      <CaseLead item={item} stage="report" />
      <PageHeader
        eyebrow="Step 5 · LLM + RAG reporting"
        title="AI-assisted clinical summary"
        description="A structured report combines predictions, explanations, safety limitations, and mock retrieved knowledge."
        aside={<StatusBadge status={item.safety.overallStatus} large />}
      />

      <section className="report-document" aria-label="NeuroSage clinical research report">
        <header className="report-masthead">
          <div className="report-brand"><span><BrainCircuit aria-hidden="true" /></span><div><strong>NeuroSage</strong><small>AI-assisted clinical research summary</small></div></div>
          <dl><div><dt>Patient</dt><dd>{item.patient.id}</dd></div><div><dt>Case</dt><dd>{item.id}</dd></div><div><dt>Safety</dt><dd><StatusBadge status={item.safety.overallStatus} /></dd></div></dl>
        </header>

        <ReportSection icon={UserRound} title="Patient summary"><p className="report-lead">{item.report.patientSummary}</p></ReportSection>

        <ReportSection icon={Gauge} title="Model findings">
          <div className="report-findings">
            {predictions.map((prediction) => (
              <div key={prediction.label}>
                <span>{prediction.label}<StatusBadge status={prediction.safetyStatus} /></span>
                <strong>{Math.round(prediction.probability * 100)}%</strong>
                <div className="metric-track"><i style={{ width: `${prediction.probability * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </ReportSection>

        <div className="report-columns">
          <ReportSection icon={Microscope} title="Supporting evidence">
            <ul className="report-list">{item.report.supportingEvidence.map((evidence) => <li key={evidence}><CheckCircle2 aria-hidden="true" />{evidence}</li>)}</ul>
          </ReportSection>
          <ReportSection icon={ShieldAlert} title="Safety considerations">
            <div className={`report-safety tone-${statusTone(item.safety.overallStatus)}`}><StatusBadge status={item.safety.overallStatus} /><strong>{item.safety.reliabilityScore.toFixed(2)} reliability</strong></div>
            <ul className="report-list safety-list">{item.report.safetyConsiderations.map((consideration) => <li key={consideration}><TriangleAlert aria-hidden="true" />{consideration}</li>)}</ul>
          </ReportSection>
        </div>

        <ReportSection icon={Stethoscope} title="Recommended interpretation"><blockquote>{item.report.recommendation}</blockquote></ReportSection>

        <ReportSection icon={BookOpenCheck} title="Retrieved evidence / knowledge sources">
          <div className="evidence-source-grid">
            {item.report.sources.map((source) => (
              <div key={source.name}><span><FileCheck2 aria-hidden="true" /></span><div><strong>{source.name}</strong><small>{source.status}</small></div></div>
            ))}
          </div>
        </ReportSection>

        <footer className="report-disclaimer"><Info aria-hidden="true" />Research demonstration only. This report is generated from static mock data and is not a validated diagnosis or clinical recommendation.</footer>
      </section>

      <div className="report-actions no-print">
        <Dialog>
          <DialogTrigger render={<Button variant="outline" size="lg" />}><FileSearch aria-hidden="true" />View evidence</DialogTrigger>
          <DialogContent className="max-w-xl p-6">
            <DialogHeader>
              <DialogTitle className="text-lg text-slate-900">Evidence used in this prototype report</DialogTitle>
              <DialogDescription>These are predefined mock references that demonstrate the intended RAG reporting structure.</DialogDescription>
            </DialogHeader>
            <div className="dialog-evidence-list">
              {item.report.sources.map((source) => <div key={source.name}><FileCheck2 aria-hidden="true" /><span><strong>{source.name}</strong><small>{source.detail}</small></span><em>{source.status}</em></div>)}
            </div>
            <DialogFooter showCloseButton />
          </DialogContent>
        </Dialog>
        <Button variant="outline" size="lg" onClick={() => window.print()}><Printer aria-hidden="true" />Print report</Button>
        <Button variant="outline" size="lg" onClick={exportReport}><Download aria-hidden="true" />Export prototype</Button>
        <Button size="lg" className="ml-auto bg-[#1f65a8] hover:bg-[#174f86]" render={<Link href="/" />}><LayoutDashboard aria-hidden="true" />Back to dashboard</Button>
      </div>
      <StageActions currentCase={item} stage="report" />
    </div>
  );
}

export function InvalidCasePage() {
  return (
    <div className="page-content error-page">
      <div className="error-illustration"><FileSearch aria-hidden="true" /></div>
      <p className="eyebrow">Assessment unavailable</p>
      <h1>Demo case not found.</h1>
      <p>The requested case ID is not part of the four predefined NeuroSage scenarios.</p>
      <Button size="lg" className="primary-route-button" render={<Link href="/" />}><LayoutDashboard aria-hidden="true" />Return to dashboard</Button>
    </div>
  );
}

export function InvalidStagePage({ item }: { item: DemoCase }) {
  return (
    <div className="page-content error-page">
      <div className="error-illustration"><Workflow aria-hidden="true" /></div>
      <p className="eyebrow">Unknown workflow stage</p>
      <h1>This assessment stage is not available.</h1>
      <p>Continue from the patient-data step for {item.patient.id}.</p>
      <Button size="lg" className="primary-route-button" render={<Link href={`/assessment/${item.id}/patient`} />}><ArrowRight aria-hidden="true" />Open patient data</Button>
    </div>
  );
}
