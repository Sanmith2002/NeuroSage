'use client';

import { Toaster } from '@/components/ui/toast';
import { AppShell, type MainView } from '@/components/neurosage-ui';
import {
  DashboardPage,
  HarmonizationPage,
  InvalidCasePage,
  InvalidStagePage,
  NewAssessmentPage,
  PatientPage,
  PredictionsPage,
  ReportPage,
  SafetyPage,
  WorkflowPage,
} from '@/components/neurosage-pages';
import {
  demoCases,
  isAssessmentStage,
  isCaseId,
  type AssessmentStage,
} from '@/lib/research';

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

export function NeuroSageApp({ view, caseId, stage }: NeuroSageAppProps) {
  const currentCase = caseId && isCaseId(caseId) ? demoCases[caseId] : undefined;
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
  else if (view === 'new') content = <NewAssessmentPage />;
  else if (view === 'workflow') content = <WorkflowPage />;
  else if (!currentCase) content = <InvalidCasePage />;
  else if (!activeStage) content = <InvalidStagePage item={currentCase} />;
  else if (activeStage === 'patient') content = <PatientPage item={currentCase} />;
  else if (activeStage === 'harmonization') content = <HarmonizationPage item={currentCase} />;
  else if (activeStage === 'predictions') content = <PredictionsPage item={currentCase} />;
  else if (activeStage === 'safety') content = <SafetyPage item={currentCase} />;
  else content = <ReportPage item={currentCase} />;

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
