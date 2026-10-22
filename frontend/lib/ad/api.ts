import type {
  ClinicalRequest,
  DemoMriCase,
  FormSpec,
  MriFields,
  MriResult,
  MriStage,
  SharedDocument,
} from '@/lib/ad/types';

// vinext inlines NEXT_PUBLIC_* at build time; the reference must stay literal for the define to apply.
export const AD_API_URL = (process.env.NEXT_PUBLIC_AD_API_URL ?? '').replace(/\/+$/, '');
// Optional and only a soft gate: anything in a client bundle is public.
const AD_API_KEY = process.env.NEXT_PUBLIC_AD_API_KEY ?? '';

export const isLiveEnabled = AD_API_URL.length > 0;

// Where the models run, for the UI copy: a loopback URL is backend/run-service.cmd on this computer,
// anything else a hosted deployment (e.g. backend/deploy-azure.cmd).
export const isLocalService = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:|\/|$)/i.test(AD_API_URL);
export const SERVICE_LABEL = !isLiveEnabled ? 'Model service not configured' : isLocalService ? 'Local models' : 'Cloud models';
export const SERVICE_LOCATION = isLocalService ? 'running on this computer' : 'running on the hosted analysis service';

const CLINICAL_TIMEOUT_MS = 60_000;
const SLOW_MS = 5_000;
export const COLD_START_MESSAGE = 'Waking up the analysis service…';

export class AdApiError extends Error {
  constructor(message: string, readonly status?: number, readonly code?: string) {
    super(message);
    this.name = 'AdApiError';
  }
}

interface CallOptions {
  timeoutMs?: number;
  onSlow?: () => void;
  signal?: AbortSignal;
}

function headers(json: boolean): HeadersInit {
  const h: Record<string, string> = {};
  if (json) h['Content-Type'] = 'application/json';
  if (AD_API_KEY) h['X-API-Key'] = AD_API_KEY;
  return h;
}

function describeError(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: Array<string | number>; msg?: string }) => {
        const where = (d.loc ?? []).filter((p) => p !== 'body').join(' › ');
        return where ? `${where}: ${d.msg}` : d.msg;
      })
      .join('; ');
  }
  if (typeof detail === 'string') return detail;
  return `Request failed (${status})`;
}

async function call<T>(path: string, init: RequestInit, opts: CallOptions = {}): Promise<T> {
  if (!isLiveEnabled) throw new AdApiError('The AD analysis service is not configured.');
  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(new DOMException('timeout', 'TimeoutError')), opts.timeoutMs ?? CLINICAL_TIMEOUT_MS);
  const slow = opts.onSlow ? setTimeout(opts.onSlow, SLOW_MS) : undefined;
  opts.signal?.addEventListener('abort', () => ctrl.abort(opts.signal?.reason), { once: true });
  try {
    const res = await fetch(`${AD_API_URL}${path}`, { ...init, signal: ctrl.signal });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new AdApiError(describeError(res.status, body), res.status);
    return body as T;
  } catch (err) {
    if (err instanceof AdApiError) throw err;
    if (ctrl.signal.aborted) throw new AdApiError('The analysis service did not respond in time. Please try again.');
    throw new AdApiError('Could not reach the analysis service. Check your connection and try again.');
  } finally {
    clearTimeout(timeout);
    if (slow) clearTimeout(slow);
  }
}

export function artifactUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  return path.startsWith('http') ? path : `${AD_API_URL}${path}`;
}

export const getFormSpec = (opts?: CallOptions) => call<FormSpec>('/v1/form-spec', { headers: headers(false) }, opts);

export const getModels = (opts?: CallOptions) => call<Record<string, unknown>>('/v1/models', { headers: headers(false) }, opts);

export const predictClinical = (req: ClinicalRequest, opts?: CallOptions) =>
  call<SharedDocument>('/v1/clinical/predict', { method: 'POST', headers: headers(true), body: JSON.stringify(req) }, opts);

export const assess = (clinical: ClinicalRequest, mriResult: MriResult | null, opts?: CallOptions) =>
  call<SharedDocument>(
    '/v1/assess',
    { method: 'POST', headers: headers(true), body: JSON.stringify({ clinical, mri_result: mriResult }) },
    opts,
  );

export const listDemoMri = (opts?: CallOptions) =>
  call<{ cases: DemoMriCase[] }>('/v1/mri/demo-cases', { headers: headers(false) }, opts).then((r) => r.cases);

export const predictDemoMri = (id: string, fields: MriFields | null, opts?: CallOptions) =>
  call<MriResult>(
    `/v1/mri/demo-cases/${encodeURIComponent(id)}/predict`,
    { method: 'POST', headers: headers(true), body: fields ? JSON.stringify(fields) : undefined },
    opts,
  );

export interface MriProgress {
  stage: MriStage;
  progress: number;
}

interface MriJob {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'error';
  stage: MriStage;
  progress: number;
  result: MriResult | null;
  error: { code?: string; message?: string } | null;
}

const MRI_POLL_MS = 2_000;
const MRI_UPLOAD_TIMEOUT_MS = 230_000; // hosted proxies end a request at 240 s
const MRI_MAX_POLL_FAILURES = 5;

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => { clearTimeout(t); reject(signal.reason); }, { once: true });
  });

/**
 * Uploads the scan as a background job and polls it. The pipeline takes several minutes on CPU, longer than a
 * hosted proxy keeps one request open, so no single request spans the whole analysis.
 */
export async function analyzeMri(
  file: File,
  fields: MriFields,
  { onStage, signal }: { onStage?: (p: MriProgress) => void; signal?: AbortSignal } = {},
): Promise<MriResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('fields', JSON.stringify(fields));
  onStage?.({ stage: 'upload', progress: 0 });

  let job = await call<MriJob>(
    '/v1/mri/jobs',
    { method: 'POST', body: form, headers: headers(false) },
    { timeoutMs: MRI_UPLOAD_TIMEOUT_MS, signal },
  ).catch((err: unknown) => {
    if (err instanceof AdApiError && err.status) throw err;
    throw new AdApiError('Could not upload the scan to the analysis service.');
  });

  let failures = 0;
  for (;;) {
    if (job.status === 'done' && job.result) return job.result;
    if (job.status === 'error') throw new AdApiError(job.error?.message ?? 'MRI analysis failed', undefined, job.error?.code);
    onStage?.({ stage: job.stage, progress: job.progress });
    await sleep(MRI_POLL_MS, signal);
    try {
      job = await call<MriJob>(`/v1/mri/jobs/${encodeURIComponent(job.job_id)}`, { headers: headers(false) }, { signal });
      failures = 0;
    } catch (err) {
      // a 404 means the job is gone (expired or the service restarted); anything else may be a network blip
      if ((err instanceof AdApiError && err.status) || ++failures >= MRI_MAX_POLL_FAILURES) throw err;
    }
  }
}
