import { useState, useEffect, useRef } from 'react'

interface Props { onComplete: (score: number, maxScore: number) => void }

const WORD_POOL = [
  'apple','table','river','cloud','mirror','piano','garden','bridge',
  'forest','candle','window','letter','mountain','bottle','clock',
  'shadow','flower','pencil','market','stone','lantern','basket',
]
const STUDY_SECS = 5
const WORDS_N    = 6

function pick(n: number) {
  const shuffled = [...WORD_POOL].sort(() => Math.random() - .5)
  return shuffled.slice(0, n)
}

type Phase = 'ready' | 'study' | 'recall' | 'done'

export default function WordRecall({ onComplete }: Props) {
  const [phase, setPhase]       = useState<Phase>('ready')
  const [words, setWords]       = useState<string[]>([])
  const [countdown, setCountdown] = useState(STUDY_SECS)
  const [typed, setTyped]       = useState('')
  const [hits, setHits]         = useState<string[]>([])
  const timerRef                = useRef<ReturnType<typeof setInterval> | null>(null)

  function startStudy() {
    const chosen = pick(WORDS_N)
    setWords(chosen)
    setCountdown(STUDY_SECS)
    setTyped('')
    setHits([])
    setPhase('study')
  }

  useEffect(() => {
    if (phase !== 'study') return
    timerRef.current = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) { clearInterval(timerRef.current!); setPhase('recall'); return 0 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current!)
  }, [phase])

  function handleSubmit() {
    const entered = typed.toLowerCase().split(/[\s,]+/).map(w => w.trim()).filter(Boolean)
    const correct = words.filter(w => entered.includes(w.toLowerCase()))
    setHits(correct)
    onComplete(correct.length, WORDS_N)
    setPhase('done')
  }

  const card: React.CSSProperties = {
    background: 'var(--surface)', border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius)', padding: '1.75rem', maxWidth: 560,
    width: '100%', margin: '0 auto',
  }

  if (phase === 'ready') return (
    <div style={card}>
      <h3 style={{ marginBottom: '.75rem' }}>Word List Recall</h3>
      <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.25rem' }}>
        You will see <strong>{WORDS_N} words</strong> for {STUDY_SECS} seconds.
        Then type back as many as you can remember.
      </p>
      <button className="btn-primary" onClick={startStudy}>Start →</button>
    </div>
  )

  if (phase === 'study') return (
    <div style={{ ...card, textAlign: 'center' }}>
      <div style={{ fontSize: '.8rem', color: 'var(--muted)', marginBottom: '1rem' }}>
        Memorise these words — {countdown}s
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.6rem', justifyContent: 'center' }}>
        {words.map(w => (
          <span key={w} style={{
            padding: '.5rem 1rem', borderRadius: 8,
            background: 'var(--brand)', color: '#fff',
            fontSize: '1.15rem', fontWeight: 600,
          }}>{w}</span>
        ))}
      </div>
      {/* countdown bar */}
      <div style={{ height: 6, borderRadius: 3, background: 'var(--border)', margin: '1.5rem 0 0' }}>
        <div style={{
          height: '100%', borderRadius: 3, background: 'var(--brand)',
          width: `${(countdown / STUDY_SECS) * 100}%`, transition: 'width 1s linear',
        }} />
      </div>
    </div>
  )

  if (phase === 'recall') return (
    <div style={card}>
      <h3 style={{ marginBottom: '.5rem' }}>What words do you remember?</h3>
      <p style={{ color: 'var(--muted)', fontSize: '.85rem', marginBottom: '1rem' }}>
        Type them separated by spaces or commas.
      </p>
      <textarea
        autoFocus
        value={typed}
        onChange={e => setTyped(e.target.value)}
        placeholder="e.g. apple table river"
        rows={3}
        style={{
          width: '100%', padding: '.75rem', borderRadius: 8,
          border: '1.5px solid var(--border)', fontSize: '1rem',
          resize: 'none', fontFamily: 'inherit',
        }}
      />
      <button className="btn-primary" style={{ marginTop: '.75rem' }} onClick={handleSubmit}
        disabled={!typed.trim()}>
        Submit →
      </button>
    </div>
  )

  // done — shown briefly before ExercisePlayer takes over with its result card
  return (
    <div style={{ ...card, textAlign: 'center', color: 'var(--muted)' }}>
      <p>You recalled <strong style={{ color: 'var(--brand)' }}>{hits.length}</strong> of {WORDS_N} words.</p>
      <div style={{ marginTop: '.75rem', fontSize: '.85rem' }}>
        Correct: {hits.join(', ') || '—'}<br />
        Words were: {words.join(', ')}
      </div>
    </div>
  )
}
