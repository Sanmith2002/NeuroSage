// In dev: Vite proxies /api → localhost:8000 (no CORS issues regardless of port).
// In prod: set VITE_API_URL=https://your-backend.onrender.com in Vercel env vars.
const BASE = import.meta.env.VITE_API_URL ?? '/api'

export async function postAssess(rawTests: Record<string, number | null>) {
  const res = await fetch(`${BASE}/assess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_tests: rawTests }),
  })
  if (!res.ok) throw new Error(`Backend error ${res.status}`)
  return res.json() as Promise<AssessResponse>
}

export async function postRecommend(payload: RecommendPayload) {
  const res = await fetch(`${BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Backend error ${res.status}`)
  return res.json() as Promise<RecommendResponse>
}

export interface AssessResponse {
  domain_z: Record<string, number | null>
  is_weak: Record<string, boolean>
  threshold: number
}

export interface RecommendPayload {
  diagnosis_probabilities: Record<string, number>
  domain_z: Record<string, number | null>
  age?: number
  education?: number
  sex?: string
  top_k?: number
}

// Shape returned by /recommend for each plan item (non-FALLBACK)
export interface Exercise {
  domain: string
  score: number
  is_weak: boolean
  will_worsen: number
  exercise_id: string
  exercise: string          // exercise name
  strategy: string
  expected_benefit_g: number
  low_benefit: boolean
  language_dependency: string
  reason: string
}

export interface RecommendResponse {
  route: string
  arm: string | null
  routing_reason: string
  reason: string
  message?: string          // present on FALLBACK
  plan: Exercise[]
}
