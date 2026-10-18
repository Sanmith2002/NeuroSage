import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { postRecommend, type RecommendResponse, type Exercise } from '../api'
import { NS_PROFILE_KEY, type NsProfile } from '../types'

interface AssessCache {
  domain_z: Record<string, number | null>
  is_weak: Record<string, boolean>
  threshold: number
}

// Map frontend diagnosis keys → backend expected labels
const PROB_MAP: Record<string, string> = {
  AD: 'alzheimer', LBD: 'lbd', PD: 'parkinson', VD: 'vascular',
}

const DOMAIN_LABELS: Record<string, string> = {
  memory: 'Memory', attention: 'Attention', executive: 'Executive Function',
  language: 'Language', visuospatial: 'Visuospatial',
}

const DOMAIN_ICONS: Record<string, string> = {
  memory: '🧠', attention: '🎯', executive: '⚡', language: '💬', visuospatial: '👁',
}

// Derive tag list from the backend boolean fields
function getTags(item: Exercise): { key: string; label: string; bg: string; color: string }[] {
  const tags = []
  if (item.is_weak)
    tags.push({ key: 'weak_now',          label: 'weak now',          bg: '#fff5f5', color: '#e53e3e' })
  if (item.will_worsen > 0)
    tags.push({ key: 'will_worsen',       label: 'predicted decline', bg: '#fffbeb', color: '#b45309' })
  if (item.low_benefit)
    tags.push({ key: 'low_benefit',       label: 'low evidence',      bg: '#f3f4f6', color: '#6b7280' })
  if (item.language_dependency === 'high')
    tags.push({ key: 'lang_dep',          label: 'language-dependent', bg: '#f0fdf4', color: '#166534' })
  return tags
}

// ── Exercise plan card ────────────────────────────────────────────────────────
function PlanCard({ item, rank, onPlay }: { item: Exercise; rank: number; onPlay: () => void }) {
  const domainLabel = DOMAIN_LABELS[item.domain] ?? item.domain
  const icon = DOMAIN_ICONS[item.domain] ?? '🔬'
  const tags = getTags(item)

  return (
    <div style={{
      border: '1.5px solid var(--border)', borderRadius: 'var(--radius)',
      padding: '1.25rem', marginBottom: '1rem', background: 'var(--surface)',
    }}>
      {/* Rank + domain */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '.6rem', marginBottom: '.6rem' }}>
        <span style={{
          width: 28, height: 28, borderRadius: '50%', background: 'var(--brand)',
          color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '.8rem', fontWeight: 700, flexShrink: 0,
        }}>{rank}</span>
        <span style={{ fontSize: '1rem' }}>{icon}</span>
        <span style={{ fontWeight: 700, fontSize: '1rem' }}>{domainLabel}</span>
      </div>

      {/* Exercise name */}
      <div style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '.35rem' }}>
        {item.exercise}
      </div>

      {/* Reason */}
      <div style={{ fontSize: '.83rem', color: 'var(--muted)', fontStyle: 'italic', marginBottom: '.75rem' }}>
        {item.reason}
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem', marginBottom: '.9rem' }}>
          {tags.map(t => (
            <span key={t.key} style={{
              padding: '.2rem .55rem', borderRadius: 20, fontSize: '.75rem',
              fontWeight: 600, background: t.bg, color: t.color,
            }}>
              {t.label}
            </span>
          ))}
        </div>
      )}

      <button className="btn-primary" style={{ height: 40, fontSize: '.9rem' }} onClick={onPlay}>
        Play this exercise →
      </button>
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function Recommendation() {
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [result, setResult]   = useState<RecommendResponse | null>(null)

  useEffect(() => {
    async function load() {
      // read localStorage
      let profile: NsProfile | null = null
      let assess: AssessCache | null = null
      try {
        profile = JSON.parse(localStorage.getItem(NS_PROFILE_KEY) ?? 'null')
        assess  = JSON.parse(localStorage.getItem('ns_assess') ?? 'null')
      } catch { /* ignore */ }

      if (!profile || !assess) {
        setError('Profile or assessment data missing. Please complete the previous steps first.')
        setLoading(false)
        return
      }

      // map probabilities: {AD:0.85,...} → {alzheimer:0.85,...}
      const mappedProbs: Record<string, number> = {}
      for (const [k, v] of Object.entries(profile.probabilities)) {
        const key = PROB_MAP[k]
        if (key) mappedProbs[key] = v
      }

      try {
        const res = await postRecommend({
          diagnosis_probabilities: mappedProbs,
          domain_z: assess.domain_z,
          age: profile.age,
          education: profile.education,
          sex: profile.sex,
          top_k: 3,
        })
        setResult(res)
        try { localStorage.setItem('ns_recommend', JSON.stringify(res)) } catch { /* ignore */ }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not reach the backend.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  function handlePlay(item: Exercise) {
    try {
      localStorage.setItem('ns_current_exercise', JSON.stringify(item))
    } catch { /* ignore */ }
    navigate('/exercise')
  }

  // patient first name
  let name = 'Patient'
  try {
    const p = JSON.parse(localStorage.getItem(NS_PROFILE_KEY) ?? 'null') as NsProfile | null
    if (p?.name) name = p.name.split(' ')[0]
  } catch { /* ignore */ }

  return (
    <div className="page">

      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">Hello, {name}</div>
      </div>

      <div className="step-indicator">
        {[1, 2, 3, 4, 5].map(n => (
          <div key={n} className={`step-dot${n === 3 ? ' active' : ''}`} />
        ))}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--muted)', padding: '3rem 2rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚙️</div>
          <p>Building your personalised exercise plan…</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="card">
          <div style={{
            background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: 8,
            padding: '.9rem 1rem', color: 'var(--danger)', fontSize: '.9rem',
          }}>
            {error}
          </div>
          <button className="btn-primary" style={{ marginTop: '1rem' }} onClick={() => navigate('/assess')}>
            ← Back to Assessment
          </button>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Routing info banner */}
          <div className="card" style={{ padding: '1rem 1.25rem' }}>
            <div style={{ fontSize: '.82rem', color: 'var(--muted)' }}>
              <strong style={{ color: 'var(--text)' }}>
                {result.route === 'FALLBACK' ? '⚠ General Plan' : `${result.arm} pathway`}
              </strong>
              {' — '}{result.reason}
            </div>
            {result.route === 'FALLBACK' && (
              <div style={{ fontSize: '.8rem', color: '#b45309', marginTop: '.4rem' }}>
                {(result as unknown as { message: string }).message}
              </div>
            )}
          </div>

          {/* Plan cards */}
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', marginBottom: '1.25rem' }}>
              Your Exercise Plan
            </h2>
            {result.plan.map((item, i) => (
              <PlanCard key={item.domain} item={item} rank={i + 1} onPlay={() => handlePlay(item)} />
            ))}
          </div>

          {/* Progress link */}
          <button
            onClick={() => navigate('/progress')}
            style={{
              background: 'transparent', border: 'none', color: 'var(--brand)',
              fontSize: '.88rem', cursor: 'pointer', textDecoration: 'underline',
            }}
          >
            View progress history →
          </button>
        </>
      )}
    </div>
  )
}
