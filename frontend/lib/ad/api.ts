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

/** POSTs the scan and reads the Server-Sent-Events stream (EventSource cannot POST). */
export async function analyzeMri(
  file: File,
  fields: MriFields,
  { onStage, signal }: { onStage?: (p: MriProgress) => void; signal?: AbortSignal } = {},
): Promise<MriResult> {
  if (!isLiveEnabled) throw new AdApiError('The AD analysis service is not configured.');
  const form = new FormData();
  form.append('file', file);
  form.append('fields', JSON.stringify(fields));
  onStage?.({ stage: 'upload', progress: 0 });

  let res: Response;
  try {
    res = await fetch(`${AD_API_URL}/v1/mri/analyze`, { method: 'POST', body: form, headers: headers(false), signal });
  } catch {
    throw new AdApiError('Could not upload the scan to the analysis service.');
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null);
    throw new AdApiError(describeError(res.status, body), res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = 'message';
      const data: string[] = [];
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data.push(line.slice(5).trim());
      }
      if (!data.length) continue;
      const payload = JSON.parse(data.join('\n'));
      if (event === 'stage') onStage?.(payload as MriProgress);
      else if (event === 'result') return payload as MriResult;
      else if (event === 'error') throw new AdApiError(payload.message ?? 'MRI analysis failed', undefined, payload.code);
    }
  }
  throw new AdApiError('The MRI analysis stream ended without a result.');
}
