import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { postAssess, type AssessResponse } from '../api'
import { NS_PROFILE_KEY, type NsProfile } from '../types'
import { saveAssessForActive } from '../storage'

// ── Test catalogue ────────────────────────────────────────────────────────────
interface TestDef {
  code: string
  label: string
  range: [number, number]
  note?: string
}

const DOMAINS: { key: string; label: string; tests: TestDef[] }[] = [
  {
    key: 'memory', label: 'Memory', tests: [
      { code: 'CRAFTVRS', label: 'Story Recall – Immediate (verbatim)',   range: [0, 44] },
      { code: 'CRAFTURS', label: 'Story Recall – Immediate (paraphrase)', range: [0, 25] },
      { code: 'CRAFTDVR', label: 'Story Recall – Delayed (verbatim)',     range: [0, 44] },
      { code: 'CRAFTDRE', label: 'Story Recall – Delayed (paraphrase)',   range: [0, 25] },
      { code: 'UDSBENTD', label: 'Figure Recall – Delayed (Benson)',      range: [0, 17] },
    ],
  },
  {
    key: 'attention', label: 'Attention', tests: [
      { code: 'DIGFORCT', label: 'Digit Span Forward – Total Correct',    range: [0, 14] },
      { code: 'DIGFORSL', label: 'Digit Span Forward – Longest Span',     range: [0, 9] },
      { code: 'DIGBACCT', label: 'Digit Span Backward – Total Correct',   range: [0, 14] },
      { code: 'DIGBACLS', label: 'Digit Span Backward – Longest Span',    range: [0, 8] },
      { code: 'TRAILA',   label: 'Trail Making A – Time (seconds)',        range: [0, 150], note: 'lower = better' },
    ],
  },
  {
    key: 'executive', label: 'Executive Function', tests: [
      { code: 'TRAILB',   label: 'Trail Making B – Time (seconds)',        range: [0, 300], note: 'lower = better' },
      { code: 'UDSVERFC', label: 'Letter Fluency F – Correct Words',       range: [0, 40] },
      { code: 'UDSVERLC', label: 'Letter Fluency L – Correct Words',       range: [0, 40] },
      { code: 'UDSVERTN', label: 'Verbal Fluency – Total Words Named',     range: [0, 77] },
    ],
  },
  {
    key: 'language', label: 'Language', tests: [
      { code: 'MINTTOTS', label: 'Object Naming (MINT) – Total Score',     range: [0, 32] },
      { code: 'ANIMALS',  label: 'Animal Naming – 60 seconds',             range: [0, 77] },
      { code: 'VEG',      label: 'Vegetable Naming – 60 seconds',          range: [0, 77] },
    ],
  },
  {
    key: 'visuospatial', label: 'Visuospatial', tests: [
      { code: 'UDSBENTC', label: 'Figure Copy (Benson)',                   range: [0, 17] },
    ],
  },
]

const DOMAIN_LABELS: Record<string, string> = {
  memory: 'Memory', attention: 'Attention', executive: 'Executive Function',
  language: 'Language', visuospatial: 'Visuospatial',
}

// ── Sample patients ───────────────────────────────────────────────────────────
// Validated raw-score sets (all within each test's valid range) derived from the
// healthy z-reference means/SDs. Each profile targets a different weak-domain
// pattern so one click demonstrates a full, realistic assessment — and across the
// profiles every exercise domain gets exercised.
interface Sample {
  key: string
  label: string
  blurb: string
  scores: Record<string, number>
}

const SAMPLES: Sample[] = [
  {
    key: 'healthy', label: 'Healthy adult', blurb: 'all domains near average',
    scores: {
      CRAFTVRS: 24, CRAFTURS: 18, CRAFTDVR: 22, CRAFTDRE: 17, UDSBENTD: 12,
      DIGFORCT: 9, DIGFORSL: 7, DIGBACCT: 8, DIGBACLS: 5, TRAILA: 29,
      TRAILB: 74, UDSVERFC: 16, UDSVERLC: 15, UDSVERTN: 32,
      MINTTOTS: 31, ANIMALS: 23, VEG: 16, UDSBENTC: 16,
    },
  },
  {
    key: 'ad', label: "Alzheimer's-type", blurb: 'memory weakest',
    scores: {
      CRAFTVRS: 7, CRAFTURS: 8, CRAFTDVR: 5, CRAFTDRE: 6, UDSBENTD: 4,
      DIGFORCT: 6, DIGFORSL: 5, DIGBACCT: 5, DIGBACLS: 4, TRAILA: 46,
      TRAILB: 139, UDSVERFC: 10, UDSVERLC: 9, UDSVERTN: 20,
      MINTTOTS: 27, ANIMALS: 14, VEG: 9, UDSBENTC: 14,
    },
  },
  {
    key: 'lbd', label: 'Lewy-body-type', blurb: 'visuospatial + attention weakest',
    scores: {
      CRAFTVRS: 16, CRAFTURS: 13, CRAFTDVR: 14, CRAFTDRE: 12, UDSBENTD: 9,
      DIGFORCT: 4, DIGFORSL: 4, DIGBACCT: 3, DIGBACLS: 3, TRAILA: 61,
      TRAILB: 154, UDSVERFC: 9, UDSVERLC: 8, UDSVERTN: 18,
      MINTTOTS: 28, ANIMALS: 16, VEG: 11, UDSBENTC: 12,
    },
  },
]

// ── Domain z-score result card ────────────────────────────────────────────────
function ZCard({ domain, z, isWeak }: { domain: string; z: number | null; isWeak: boolean }) {
  const label = DOMAIN_LABELS[domain] ?? domain
  const pct = z === null ? 50 : Math.min(100, Math.max(0, ((z + 3) / 6) * 100))
  const color = isWeak ? '#e53e3e' : z !== null && z >= 0 ? '#38a169' : '#d97706'
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '.3rem' }}>
        <span style={{ fontWeight: 600, fontSize: '.9rem' }}>{label}</span>
        <span style={{ fontSize: '.9rem', color, fontWeight: 700 }}>
          {z === null ? 'n/a' : z.toFixed(2)}
          {isWeak && ' ⚠ weak'}
        </span>
      </div>
      <div style={{ height: 8, borderRadius: 4, background: '#e5e7eb', position: 'relative' }}>
        {z !== null && (
          <div style={{ height: '100%', width: `${pct}%`, borderRadius: 4, background: color, transition: 'width .4s' }} />
        )}
        {/* zero line */}
        <div style={{ position: 'absolute', top: 0, left: '50%', width: 2, height: '100%', background: '#9ca3af' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.7rem', color: '#9ca3af', marginTop: '.15rem' }}>
        <span>−3</span><span>0</span><span>+3</span>
      </div>
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function Assessment() {
  const navigate = useNavigate()

  // load patient name from localStorage for greeting
  let patientName = 'Patient'
  try {
    const p = JSON.parse(localStorage.getItem(NS_PROFILE_KEY) ?? 'null') as NsProfile | null
    if (p?.name) patientName = p.name.split(' ')[0]
  } catch { /* ignore */ }

  // raw score state: code → string (empty = not administered)
  const allCodes = DOMAINS.flatMap(d => d.tests.map(t => t.code))
  const [scores, setScores] = useState<Record<string, string>>(
    Object.fromEntries(allCodes.map(c => [c, '']))
  )

  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [result, setResult]     = useState<AssessResponse | null>(null)

  function setScore(code: string, val: string) {
    setScores(s => ({ ...s, [code]: val }))
  }

  function fillSample(sample: Sample) {
    setScores(Object.fromEntries(
      allCodes.map(c => [c, sample.scores[c] != null ? String(sample.scores[c]) : ''])
    ))
    setResult(null)
    setError(null)
  }

  function clearScores() {
    setScores(Object.fromEntries(allCodes.map(c => [c, ''])))
    setResult(null)
    setError(null)
  }

  async function handleAssess() {
    setLoading(true)
    setError(null)
    setResult(null)

    const rawTests: Record<string, number | null> = {}
    for (const code of allCodes) {
      const v = scores[code].trim()
      rawTests[code] = v === '' ? null : Number(v)
    }

    try {
      const res = await postAssess(rawTests)
      setResult(res)
      // save to localStorage for Screen 3 (+ per-patient copy)
      try { localStorage.setItem('ns_assess', JSON.stringify(res)) } catch { /* ignore */ }
      saveAssessForActive(res)
      // scroll to results
      setTimeout(() => document.getElementById('results-anchor')?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reach the backend. Is it running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  function handleNext() {
    navigate('/recommend')
  }

  const filledCount = allCodes.filter(c => scores[c].trim() !== '').length

  return (
    <div className="page">

      {/* Header */}
      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">Hello, {patientName}</div>
      </div>

      <div className="step-indicator">
        {[1, 2, 3, 4, 5].map(n => (
          <div key={n} className={`step-dot${n === 2 ? ' active' : ''}`} />
        ))}
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.2rem', marginBottom: '.4rem' }}>Cognitive Assessment</h2>
        <p style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: '1rem' }}>
          Enter available test scores below. Leave any untested fields blank — the system
          will use whichever scores are provided.
        </p>

        {/* Quick-fill sample patients */}
        <div style={{
          background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8,
          padding: '.85rem 1rem', marginBottom: '1.5rem',
        }}>
          <div style={{ fontSize: '.78rem', fontWeight: 600, marginBottom: '.6rem', color: 'var(--text)' }}>
            Quick fill with a validated sample patient
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem' }}>
            {SAMPLES.map(s => (
              <button
                key={s.key}
                type="button"
                onClick={() => fillSample(s)}
                title={s.blurb}
                style={{
                  flex: '1 1 150px', minWidth: 140, padding: '.5rem .75rem',
                  borderRadius: 8, border: '1.5px solid var(--border)', background: 'var(--surface)',
                  cursor: 'pointer', textAlign: 'left', lineHeight: 1.25,
                }}
              >
                <span style={{ fontSize: '.85rem', fontWeight: 600, color: 'var(--brand)' }}>{s.label}</span>
                <br />
                <span style={{ fontSize: '.72rem', color: 'var(--muted)' }}>{s.blurb}</span>
              </button>
            ))}
            <button
              type="button"
              onClick={clearScores}
              style={{
                padding: '.5rem .75rem', borderRadius: 8, border: '1.5px solid var(--border)',
                background: 'var(--surface)', cursor: 'pointer', fontSize: '.8rem', color: 'var(--muted)',
                alignSelf: 'stretch',
              }}
            >
              Clear
            </button>
          </div>
        </div>

        {DOMAINS.map(dom => (
          <div key={dom.key} style={{ marginBottom: '1.5rem' }}>
            <div style={{
              fontSize: '.75rem', fontWeight: 700, letterSpacing: '.06em',
              color: 'var(--brand)', textTransform: 'uppercase', marginBottom: '.75rem',
              borderBottom: '1px solid var(--border)', paddingBottom: '.35rem',
            }}>
              {dom.label}
            </div>

            {dom.tests.map(t => (
              <div className="field" key={t.code} style={{ marginBottom: '.75rem' }}>
                <label style={{ fontSize: '.82rem' }}>
                  {t.label}
                  <span className="hint"> ({t.range[0]}–{t.range[1]}{t.note ? `, ${t.note}` : ''})</span>
                </label>
                <input
                  type="number"
                  min={t.range[0]}
                  max={t.range[1]}
                  step={1}
                  placeholder="—"
                  value={scores[t.code]}
                  onChange={e => setScore(t.code, e.target.value)}
                  style={{ maxWidth: 120 }}
                />
              </div>
            ))}
          </div>
        ))}

        {error && (
          <div style={{
            background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: 8,
            padding: '.75rem 1rem', color: 'var(--danger)', fontSize: '.85rem',
            marginBottom: '1rem',
          }}>
            {error}
          </div>
        )}

        <button
          className="btn-primary"
          onClick={handleAssess}
          disabled={loading || filledCount === 0}
        >
          {loading ? 'Analysing…' : `Calculate Domain Scores (${filledCount} / ${allCodes.length} entered)`}
        </button>
      </div>

      {/* Results section — appears after successful assess call */}
      {result && (
        <div className="card" id="results-anchor">
          <h2 style={{ fontSize: '1.15rem', marginBottom: '1.25rem' }}>Domain Results</h2>

          {Object.entries(result.domain_z).map(([domain, z]) => (
            <ZCard key={domain} domain={domain} z={z} isWeak={result.is_weak[domain]} />
          ))}

          <div style={{
            fontSize: '.78rem', color: 'var(--muted)', margin: '1rem 0',
            padding: '.6rem .75rem', background: 'var(--bg)', borderRadius: 6,
          }}>
            Scores are z-scored against a healthy reference group. A score below{' '}
            <strong>{result.threshold}</strong> (SD from the mean) is flagged as weak.
            Bars to the left of centre mean below-average performance.
          </div>

          <button className="btn-primary" onClick={handleNext}>
            Get Exercise Recommendations →
          </button>
        </div>
      )}
    </div>
  )
}
