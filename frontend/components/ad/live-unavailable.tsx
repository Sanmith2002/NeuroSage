'use client';

import Link from 'next/link';
import { ArrowLeft, PlugZap } from 'lucide-react';

import { Button } from '@/components/ui/button';

export function LiveModeUnavailable() {
  return (
    <div className="page-content error-page">
      <div className="error-illustration"><PlugZap aria-hidden="true" /></div>
      <p className="eyebrow">Model service not configured</p>
      <h1>The AD analysis service is not configured.</h1>
      <p>Start the local model service (<code>services/ad-service/run-service.cmd</code>) and set <code>NEXT_PUBLIC_AD_API_URL=http://127.0.0.1:8000</code> in <code>.env.local</code>, then restart <code>npm run dev</code>.</p>
      <Button size="lg" variant="outline" render={<Link href="/" />}><ArrowLeft aria-hidden="true" />Back to dashboard</Button>
    </div>
  );
}
