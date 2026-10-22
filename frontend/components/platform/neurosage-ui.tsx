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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  assessmentStages,
  caseHref,
  type AssessmentStage,
  type CaseView,
  type SafetyStatus,
} from '@/lib/assessment';

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
  currentCase?: CaseView;
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
  currentCase?: CaseView;
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
                <CircleGauge aria-hidden="true" /> Local models
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

export function AssessmentStepper({ currentCase, stage }: { currentCase: CaseView; stage: AssessmentStage }) {
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
  currentCase: CaseView;
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
            <ArrowLeft aria-hidden="true" /> New patient
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

export function Principle({ children }: { children: ReactNode }) {
  return (
    <aside className="principle-callout">
      <Sparkles aria-hidden="true" />
      <div><strong>NeuroSage principle</strong><p>{children}</p></div>
    </aside>
  );
}
