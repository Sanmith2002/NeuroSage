import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import WordRecall from '../games/WordRecall'
import DigitSpan from '../games/DigitSpan'
import NBack from '../games/NBack'
import VerbalFluency from '../games/VerbalFluency'
import VisualSearch from '../games/VisualSearch'
import type { Exercise } from '../api'

const DOMAIN_LABELS: Record<string, string> = {
  memory: 'Memory', attention: 'Attention', executive: 'Executive Function',
  language: 'Language', visuospatial: 'Visuospatial',
}
const DOMAIN_ICONS: Record<string, string> = {
  memory: '🧠', attention: '🎯', executive: '⚡', language: '💬', visuospatial: '👁',
}

interface GameResult { score: number; maxScore: number }

function saveResult(ex: Exercise, score: number, maxScore: number) {
  try {
    const prev = JSON.parse(localStorage.getItem('ns_results') ?? '[]') as object[]
    prev.push({
      date: new Date().toISOString(),
      domain: ex.domain,
      exercise: ex.exercise,
      score,
      maxScore,
      pct: maxScore > 0 ? Math.round((score / maxScore) * 100) : 0,
    })
    localStorage.setItem('ns_results', JSON.stringify(prev))
  } catch { /* ignore */ }
}

export default function ExercisePlayer() {
  const navigate = useNavigate()
  const [done, setDone] = useState<GameResult | null>(null)

  let ex: Exercise | null = null
  try {
    ex = JSON.parse(localStorage.getItem('ns_current_exercise') ?? 'null')
  } catch { /* ignore */ }

  if (!ex) {
    return (
      <div className="page">
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
            No exercise selected. Go back to Recommendations.
          </p>
          <button className="btn-primary" onClick={() => navigate('/recommend')}>← Back</button>
        </div>
      </div>
    )
  }

  function handleComplete(score: number, maxScore: number) {
    saveResult(ex!, score, maxScore)
    setDone({ score, maxScore })
  }

  const icon  = DOMAIN_ICONS[ex.domain] ?? '🔬'
  const label = DOMAIN_LABELS[ex.domain] ?? ex.domain
  const pct   = done ? (done.maxScore > 0 ? Math.round((done.score / done.maxScore) * 100) : 0) : 0

  return (
    <div className="page">
      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">{icon} {label} Exercise</div>
      </div>

      <div className="step-indicator">
        {[1,2,3,4,5].map(n => (
          <div key={n} className={`step-dot${n === 4 ? ' active' : ''}`} />
        ))}
      </div>

      {/* Result summary overlay */}
      {done ? (
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '.5rem' }}>
            {pct >= 70 ? '🎉' : pct >= 40 ? '👍' : '💪'}
          </div>
          <h2 style={{ marginBottom: '.35rem' }}>{ex.exercise}</h2>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--brand)', margin: '1rem 0' }}>
            {done.score} / {done.maxScore}
            <span style={{ fontSize: '1rem', color: 'var(--muted)', marginLeft: '.5rem' }}>({pct}%)</span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.5rem' }}>
            {pct >= 70 ? 'Great work! Consistent practice builds lasting improvement.'
              : pct >= 40 ? 'Good effort. Keep practising to strengthen this domain.'
              : 'Every session counts. Try again to see improvement over time.'}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
            <button className="btn-primary" onClick={() => { setDone(null) }}>
              Play Again
            </button>
            <button className="btn-primary" style={{ background: 'var(--muted)' }}
              onClick={() => navigate('/recommend')}>
              ← Back to Plan
            </button>
            <button className="btn-primary" style={{ background: 'transparent', color: 'var(--brand)', border: '1.5px solid var(--brand)' }}
              onClick={() => navigate('/progress')}>
              View Progress →
            </button>
          </div>
        </div>
      ) : (
        /* Game header + active game */
        <>
          <div className="card" style={{ padding: '1rem 1.25rem', marginBottom: 0 }}>
            <div style={{ fontWeight: 700 }}>{ex.exercise}</div>
            <div style={{ fontSize: '.82rem', color: 'var(--muted)', marginTop: '.2rem' }}>{ex.reason}</div>
          </div>

          {ex.domain === 'memory'      && <WordRecall    onComplete={handleComplete} />}
          {ex.domain === 'attention'   && <DigitSpan     onComplete={handleComplete} />}
          {ex.domain === 'executive'   && <NBack         onComplete={handleComplete} />}
          {ex.domain === 'language'    && <VerbalFluency onComplete={handleComplete} />}
          {ex.domain === 'visuospatial'&& <VisualSearch  onComplete={handleComplete} />}
        </>
      )}
    </div>
  )
}
