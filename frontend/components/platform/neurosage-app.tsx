'use client';

import { useSyncExternalStore } from 'react';

import { Toaster } from '@/components/ui/toast';
import { AppShell, type MainView } from '@/components/platform/neurosage-ui';
import {
  DashboardPage,
  InvalidCasePage,
  InvalidStagePage,
  WorkflowPage,
} from '@/components/platform/neurosage-pages';
import {
  LiveCaseLoading,
  LiveHarmonizationPage,
  LivePatientPage,
  LivePredictionsPage,
  LiveReportPage,
  LiveSafetyPage,
} from '@/components/ad/results';
import { AdLiveForm } from '@/components/ad/live-form';
import { LiveModeUnavailable } from '@/components/ad/live-unavailable';
import { isLiveEnabled } from '@/lib/ad/api';
import { toViewModel, useLiveCase } from '@/lib/ad/live-cases';
import { isAssessmentStage, type AssessmentStage } from '@/lib/assessment';

interface NeuroSageAppProps {
  view: MainView;
  caseId?: string;
  stage?: string;
}

const pageLabels: Record<AssessmentStage, string> = {
  patient: 'Patient data',
  harmonization: 'Data harmonization',
  predictions: 'AI predictions',
  safety: 'Safety assessment',
  report: 'Clinical report',
};

const stagePages = {
  patient: LivePatientPage,
  harmonization: LiveHarmonizationPage,
  predictions: LivePredictionsPage,
  safety: LiveSafetyPage,
  report: LiveReportPage,
};

const noopSubscribe = () => () => {};
// false during SSR and hydration, true afterwards: cases only exist in this tab's sessionStorage
const useHydrated = () => useSyncExternalStore(noopSubscribe, () => true, () => false);

export function NeuroSageApp({ view, caseId, stage }: NeuroSageAppProps) {
  const hydrated = useHydrated();
  const live = useLiveCase(caseId);
  const currentCase = live ? toViewModel(live) : undefined;
  const activeStage = stage && isAssessmentStage(stage) ? stage : undefined;
  const pageLabel = view === 'dashboard'
    ? 'Dashboard'
    : view === 'new'
      ? 'New assessment'
      : view === 'workflow'
        ? 'Research workflow'
        : activeStage
          ? pageLabels[activeStage]
          : 'Assessment';

  let content;
  if (view === 'dashboard') content = <DashboardPage />;
  else if (view === 'new') content = isLiveEnabled ? <AdLiveForm /> : <LiveModeUnavailable />;
  else if (view === 'workflow') content = <WorkflowPage />;
  else if (!hydrated) content = <LiveCaseLoading />;
  else if (!live || !currentCase) content = <InvalidCasePage />;
  else if (!activeStage) content = <InvalidStagePage item={currentCase} />;
  else {
    const Page = stagePages[activeStage];
    content = <Page item={currentCase} live={live} />;
  }

  return (
    <Toaster>
      <AppShell
        currentCase={currentCase}
        activeView={view}
        activeStage={activeStage}
        pageLabel={pageLabel}
      >
        {content}
      </AppShell>
    </Toaster>
  );
}
