import { useNavigate } from 'react-router-dom'
import { NS_PROFILE_KEY, type NsProfile } from '../types'

interface SessionResult {
  date: string
  domain: string
  exercise: string
  score: number
  maxScore: number
  pct: number
}

const DOMAIN_LABELS: Record<string, string> = {
  memory: 'Memory', attention: 'Attention', executive: 'Executive Function',
  language: 'Language', visuospatial: 'Visuospatial',
}
const DOMAIN_ICONS: Record<string, string> = {
  memory: '🧠', attention: '🎯', executive: '⚡', language: '💬', visuospatial: '👁',
}
const DOMAIN_COLORS: Record<string, string> = {
  memory: '#4f6ef7', attention: '#38a169', executive: '#d97706',
  language: '#9f7aea', visuospatial: '#e53e3e',
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  } catch { return iso }
}

function pctColor(pct: number) {
  if (pct >= 70) return '#38a169'
  if (pct >= 40) return '#d97706'
  return '#e53e3e'
}

// ── Per-domain average ──────────────────────────────────────────────────────
function DomainSummary({ domain, results }: { domain: string; results: SessionResult[] }) {
  const avg = Math.round(results.reduce((s, r) => s + r.pct, 0) / results.length)
  const color = DOMAIN_COLORS[domain] ?? 'var(--brand)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '.75rem', marginBottom: '.75rem' }}>
      <span style={{ fontSize: '1.1rem', width: 24, textAlign: 'center' }}>{DOMAIN_ICONS[domain] ?? '🔬'}</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '.2rem' }}>
          <span style={{ fontSize: '.85rem', fontWeight: 600 }}>{DOMAIN_LABELS[domain] ?? domain}</span>
          <span style={{ fontSize: '.82rem', color: pctColor(avg), fontWeight: 700 }}>{avg}% avg · {results.length} session{results.length !== 1 ? 's' : ''}</span>
        </div>
        <div style={{ height: 7, borderRadius: 4, background: 'var(--border)' }}>
          <div style={{ height: '100%', borderRadius: 4, background: color, width: `${avg}%`, transition: 'width .4s' }} />
        </div>
      </div>
    </div>
  )
}

// ── Single session row ──────────────────────────────────────────────────────
function SessionRow({ result }: { result: SessionResult }) {
  const color = DOMAIN_COLORS[result.domain] ?? 'var(--brand)'
  const icon  = DOMAIN_ICONS[result.domain] ?? '🔬'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '.75rem',
      padding: '.85rem 0', borderBottom: '1px solid var(--border)',
    }}>
      {/* Domain colour dot */}
      <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, flexShrink: 0 }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: '.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {icon} {result.exercise}
        </div>
        <div style={{ fontSize: '.75rem', color: 'var(--muted)', marginTop: '.1rem' }}>
          {DOMAIN_LABELS[result.domain] ?? result.domain} · {formatDate(result.date)}
        </div>
      </div>

      {/* Score badge */}
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{ fontWeight: 700, fontSize: '.95rem', color: pctColor(result.pct) }}>
          {result.pct}%
        </div>
        <div style={{ fontSize: '.72rem', color: 'var(--muted)' }}>
          {result.score}/{result.maxScore}
        </div>
      </div>
    </div>
  )
}

// ── Main screen ─────────────────────────────────────────────────────────────
export default function Progress() {
  const navigate = useNavigate()

  let name = 'Patient'
  let results: SessionResult[] = []
  try {
    const p = JSON.parse(localStorage.getItem(NS_PROFILE_KEY) ?? 'null') as NsProfile | null
    if (p?.name) name = p.name.split(' ')[0]
    results = JSON.parse(localStorage.getItem('ns_results') ?? '[]')
  } catch { /* ignore */ }

  // sort newest first
  const sorted = [...results].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  // group by domain for summary
  const byDomain: Record<string, SessionResult[]> = {}
  for (const r of results) {
    if (!byDomain[r.domain]) byDomain[r.domain] = []
    byDomain[r.domain].push(r)
  }
  const domains = Object.keys(byDomain).sort()

  return (
    <div className="page">

      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">Hello, {name}</div>
      </div>

      <div className="step-indicator">
        {[1, 2, 3, 4, 5].map(n => (
          <div key={n} className={`step-dot${n === 5 ? ' active' : ''}`} />
        ))}
      </div>

      {/* Empty state */}
      {results.length === 0 ? (
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '.75rem' }}>📊</div>
          <h2 style={{ marginBottom: '.5rem' }}>No sessions yet</h2>
          <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.25rem' }}>
            Complete your first exercise to see your progress here.
          </p>
          <button className="btn-primary" onClick={() => navigate('/recommend')}>
            Go to Recommendations →
          </button>
        </div>
      ) : (
        <>
          {/* Domain summary */}
          <div className="card">
            <h2 style={{ fontSize: '1.1rem', marginBottom: '1.25rem' }}>
              Summary · {results.length} session{results.length !== 1 ? 's' : ''}
            </h2>
            {domains.map(d => (
              <DomainSummary key={d} domain={d} results={byDomain[d]} />
            ))}
          </div>

          {/* Session history */}
          <div className="card">
            <h2 style={{ fontSize: '1.1rem', marginBottom: '.25rem' }}>Session History</h2>
            <p style={{ fontSize: '.78rem', color: 'var(--muted)', marginBottom: '.5rem' }}>
              Most recent first
            </p>
            {sorted.map((r, i) => (
              <SessionRow key={i} result={r} />
            ))}
          </div>

          {/* Navigation */}
          <button className="btn-primary" onClick={() => navigate('/recommend')}
            style={{ maxWidth: 560, width: '100%' }}>
            Back to Recommendations →
          </button>
        </>
      )}
    </div>
  )
}
