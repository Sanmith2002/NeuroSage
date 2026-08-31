'use client';

import { useEffect, useState, type ReactNode } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  ClipboardPlus,
  FileText,
  LayoutDashboard,
  LoaderCircle,
  Menu,
  OctagonX,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Workflow,
  X,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  assessmentStages,
  caseHref,
  type AssessmentStage,
  type DemoCase,
  type FeatureContribution,
  type Prediction,
  type SafetyStatus,
} from '@/lib/research';

export type MainView = 'dashboard' | 'new' | 'workflow' | 'assessment';

const statusIcons = {
  TRUST: CheckCircle2,
  CAUTION: TriangleAlert,
  DEFER: OctagonX,
};

export function statusTone(status: SafetyStatus): string {
  return status.toLowerCase();
}

export function StatusBadge({ status, large = false }: { status: SafetyStatus; large?: boolean }) {
  const Icon = statusIcons[status];
  return (
    <span className={`status-badge tone-${statusTone(status)} ${large ? 'is-large' : ''}`}>
      <Icon aria-hidden="true" />
      {status}
    </span>
  );
}

function AppNavLink({
  href,
  label,
  icon: Icon,
  active,
  disabled,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: typeof Activity;
  active?: boolean;
  disabled?: boolean;
  onNavigate?: () => void;
}) {
  if (disabled) {
    return (
      <span className="nav-link is-disabled" aria-disabled="true">
        <Icon aria-hidden="true" />
        <span>{label}</span>
      </span>
    );
  }

  return (
    <Link href={href} className={`nav-link ${active ? 'is-active' : ''}`} onClick={onNavigate}>
      <Icon aria-hidden="true" />
      <span>{label}</span>
    </Link>
  );
}

function SidebarContent({
  currentCase,
  activeView,
  activeStage,
  onNavigate,
}: {
  currentCase?: DemoCase;
  activeView: MainView;
  activeStage?: AssessmentStage;
  onNavigate?: () => void;
}) {
  const stageIcons = [Activity, Workflow, BrainCircuit, ShieldCheck, FileText];

  return (
    <>
      <Link href="/" className="brand-lockup" aria-label="NeuroSage dashboard" onClick={onNavigate}>
        <span className="brand-mark"><BrainCircuit aria-hidden="true" /></span>
        <span><strong>NeuroSage</strong><small>Clinical AI research</small></span>
      </Link>

      <nav className="mt-9 space-y-1" aria-label="Primary navigation">
        <AppNavLink href="/" label="Dashboard" icon={LayoutDashboard} active={activeView === 'dashboard'} onNavigate={onNavigate} />
        <AppNavLink href="/assessment/new" label="New assessment" icon={ClipboardPlus} active={activeView === 'new'} onNavigate={onNavigate} />
        <AppNavLink href="/workflow" label="Research workflow" icon={Workflow} active={activeView === 'workflow'} onNavigate={onNavigate} />

        <div className="nav-divider"><span>Assessment flow</span></div>
        {assessmentStages.map((stage, index) => (
          <AppNavLink
            key={stage.key}
            href={currentCase ? caseHref(currentCase.id, stage.key) : '#'}
            label={stage.label}
            icon={stageIcons[index]}
            active={activeView === 'assessment' && activeStage === stage.key}
            disabled={!currentCase}
            onNavigate={onNavigate}
          />
        ))}
      </nav>

      <div className="sidebar-footer">
        {currentCase && (
          <div className="active-case-mini">
            <span>{currentCase.shortLabel}</span>
            <strong>{currentCase.patient.id}</strong>
            <StatusBadge status={currentCase.safety.overallStatus} />
          </div>
        )}
        <div className="prototype-note">
          <ShieldCheck aria-hidden="true" />
          <div><strong>Research prototype</strong><span>Not for clinical diagnosis</span></div>
        </div>
      </div>
    </>
  );
}

export function AppShell({
  children,
  currentCase,
  activeView,
  activeStage,
  pageLabel,
}: {
  children: ReactNode;
  currentCase?: DemoCase;
  activeView: MainView;
  activeStage?: AssessmentStage;
  pageLabel: string;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  return (
    <TooltipProvider>
      <main className="app-frame min-h-screen bg-background text-foreground">
        <aside className="sidebar-shell hidden lg:flex">
          <SidebarContent currentCase={currentCase} activeView={activeView} activeStage={activeStage} />
        </aside>

        {mobileOpen && (
          <div className="mobile-navigation lg:hidden">
            <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
            <aside className="mobile-sidebar" aria-label="Mobile navigation">
              <Tooltip>
                <TooltipTrigger
                  render={<button type="button" className="icon-button mobile-close" aria-label="Close navigation" />}
                  onClick={() => setMobileOpen(false)}
                >
                  <X aria-hidden="true" />
                </TooltipTrigger>
                <TooltipContent>Close navigation</TooltipContent>
              </Tooltip>
              <SidebarContent
                currentCase={currentCase}
                activeView={activeView}
                activeStage={activeStage}
                onNavigate={() => setMobileOpen(false)}
              />
            </aside>
          </div>
        )}

        <section className="content-shell">
          <header className="topbar">
            <div className="flex items-center gap-3">
              <Tooltip>
                <TooltipTrigger
                  render={<button type="button" className="icon-button lg:hidden" aria-label="Open navigation" />}
                  onClick={() => setMobileOpen(true)}
                >
                  <Menu aria-hidden="true" />
                </TooltipTrigger>
                <TooltipContent>Open navigation</TooltipContent>
              </Tooltip>
              <div className="flex items-center gap-3 lg:hidden">
                <span className="brand-mark brand-mark-small"><BrainCircuit aria-hidden="true" /></span>
                <strong className="text-[15px]">NeuroSage</strong>
              </div>
              <div className="hidden lg:block">
                <p className="eyebrow">Clinical research workspace</p>
                <p className="text-sm font-semibold text-slate-700">{pageLabel}</p>
              </div>
            </div>

            <div className="topbar-actions">
              {currentCase && (
                <Badge variant="outline" className="case-context-badge">
                  {currentCase.patient.id} · {currentCase.shortLabel}
                </Badge>
              )}
              <Badge variant="outline" className="demo-ready-badge">
                <CircleGauge aria-hidden="true" /> Viva demo
              </Badge>
            </div>
          </header>

          {children}
        </section>
      </main>
    </TooltipProvider>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  aside,
}: {
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {aside && <div className="page-header-aside">{aside}</div>}
    </header>
  );
}

export function AssessmentStepper({ currentCase, stage }: { currentCase: DemoCase; stage: AssessmentStage }) {
  const currentIndex = assessmentStages.findIndex((item) => item.key === stage);

  return (
    <nav className="assessment-stepper" aria-label="Assessment progress">
      {assessmentStages.map((item, index) => {
        const isCurrent = item.key === stage;
        const isComplete = index < currentIndex;
        return (
          <div className="stepper-segment" key={item.key}>
            <Link
              href={caseHref(currentCase.id, item.key)}
              className={`stepper-link ${isCurrent ? 'is-current' : ''} ${isComplete ? 'is-complete' : ''}`}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <span className="step-number">{isComplete ? <Check aria-hidden="true" /> : index + 1}</span>
              <span><small>Step {index + 1}</small><strong>{item.shortLabel}</strong></span>
            </Link>
            {index < assessmentStages.length - 1 && <ChevronRight className="step-chevron" aria-hidden="true" />}
          </div>
        );
      })}
    </nav>
  );
}

export function StageActions({
  currentCase,
  stage,
  nextLabel,
}: {
  currentCase: DemoCase;
  stage: AssessmentStage;
  nextLabel?: string;
}) {
  const index = assessmentStages.findIndex((item) => item.key === stage);
  const previous = assessmentStages[index - 1];
  const next = assessmentStages[index + 1];

  return (
    <footer className="stage-actions">
      <div>
        {previous ? (
          <Button variant="outline" size="lg" render={<Link href={caseHref(currentCase.id, previous.key)} />}>
            <ArrowLeft aria-hidden="true" /> Back
          </Button>
        ) : (
          <Button variant="outline" size="lg" render={<Link href="/assessment/new" />}>
            <ArrowLeft aria-hidden="true" /> Change patient
          </Button>
        )}
      </div>
      <div className="stage-position">{index + 1} of {assessmentStages.length}</div>
      <div>
        {next ? (
          <Button size="lg" className="h-10 bg-[#1f65a8] px-4 hover:bg-[#174f86]" render={<Link href={caseHref(currentCase.id, next.key)} />}>
            {nextLabel ?? `Continue to ${next.shortLabel}`} <ArrowRight aria-hidden="true" />
          </Button>
        ) : (
          <Button size="lg" className="h-10 bg-[#1f65a8] px-4 hover:bg-[#174f86]" render={<Link href="/" />}>
            Back to dashboard <LayoutDashboard aria-hidden="true" />
          </Button>
        )}
      </div>
    </footer>
  );
}

export function ScenarioCard({ item, compact = false }: { item: DemoCase; compact?: boolean }) {
  const featured = item.id === 'CASE-C';
  const probability = item.adPredictions[0].probability;

  return (
    <article className={`scenario-card tone-${statusTone(item.safety.overallStatus)} ${featured ? 'is-featured' : ''} ${compact ? 'is-compact' : ''}`}>
      <div className="scenario-topline">
        <span className="scenario-label">{item.shortLabel}{featured ? ' · Key viva scenario' : ''}</span>
        <StatusBadge status={item.safety.overallStatus} />
      </div>
      <h3>{item.title}</h3>
      <p>{item.description}</p>
      {featured && !compact && (
        <div className="confidence-contrast" aria-label="High probability but low reliability">
          <span><strong>{Math.round(probability * 100)}%</strong> AD probability</span>
          <ArrowRight aria-hidden="true" />
          <span><strong>{item.safety.reliabilityScore.toFixed(2)}</strong> reliability</span>
        </div>
      )}
      <Link href={caseHref(item.id, 'patient')} className="scenario-action">
        Start demo <ArrowRight aria-hidden="true" />
      </Link>
    </article>
  );
}

export function ProcessingBanner({
  steps,
  completeLabel,
}: {
  steps: string[];
  completeLabel: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const reducedMotionTimer = window.setTimeout(() => {
        setActiveIndex(steps.length - 1);
        setComplete(true);
      }, 0);
      return () => window.clearTimeout(reducedMotionTimer);
    }

    const timers = steps.slice(1).map((_, index) => (
      window.setTimeout(() => setActiveIndex(index + 1), (index + 1) * 330)
    ));
    const completion = window.setTimeout(() => setComplete(true), steps.length * 330 + 140);
    return () => {
      timers.forEach(window.clearTimeout);
      window.clearTimeout(completion);
    };
  }, [steps]);

  const progress = complete ? 100 : Math.round(((activeIndex + 1) / (steps.length + 1)) * 100);

  return (
    <section className={`processing-banner ${complete ? 'is-complete' : ''}`} aria-live="polite">
      <div className="processing-icon">
        {complete ? <CheckCircle2 aria-hidden="true" /> : <LoaderCircle className="animate-spin" aria-hidden="true" />}
      </div>
      <div className="processing-copy">
        <span>{complete ? completeLabel : steps[activeIndex]}</span>
        <Progress value={progress} aria-label="Processing progress" />
      </div>
      {!complete && (
        <button
          type="button"
          className="text-action"
          onClick={() => {
            setActiveIndex(steps.length - 1);
            setComplete(true);
          }}
        >
          Show results
        </button>
      )}
    </section>
  );
}

export function ProbabilityBars({ predictions }: { predictions: Prediction[] }) {
  return (
    <div className="probability-list">
      {predictions.map((prediction) => (
        <div className="probability-row" key={prediction.label}>
          <div><span>{prediction.label}</span><strong>{Math.round(prediction.probability * 100)}%</strong></div>
          <div className="metric-track" aria-label={`${prediction.label} ${Math.round(prediction.probability * 100)} percent`}>
            <span style={{ width: `${prediction.probability * 100}%` }} />
          </div>
          <StatusBadge status={prediction.safetyStatus} />
        </div>
      ))}
    </div>
  );
}

export function FeatureImportance({ features }: { features: FeatureContribution[] }) {
  return (
    <div className="feature-list">
      <div className="feature-legend"><span><i className="supports" />Supports</span><span><i className="reduces" />Reduces</span></div>
      {features.map((feature) => (
        <div className="feature-row" key={feature.label}>
          <span>{feature.label}</span>
          <div className="feature-track">
            <i className={feature.direction} style={{ width: `${Math.max(feature.value * 100, 3)}%` }} />
          </div>
          <strong>{feature.value.toFixed(2)}</strong>
        </div>
      ))}
    </div>
  );
}

export function DemoPrinciple({ children }: { children: ReactNode }) {
  return (
    <aside className="principle-callout">
      <Sparkles aria-hidden="true" />
      <div><strong>NeuroSage principle</strong><p>{children}</p></div>
    </aside>
  );
}
