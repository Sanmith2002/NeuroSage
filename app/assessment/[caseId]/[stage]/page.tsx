import { NeuroSageApp } from '@/components/neurosage-app';

export default async function AssessmentRoute({
  params,
}: {
  params: Promise<{ caseId: string; stage: string }>;
}) {
  const { caseId, stage } = await params;
  return <NeuroSageApp view="assessment" caseId={caseId} stage={stage} />;
}
