import { useState, useEffect, useRef } from 'react'

interface Props { onComplete: (score: number, maxScore: number) => void }

const MAX_SPAN = 9

function randDigits(len: number) {
  return Array.from({ length: len }, () => Math.floor(Math.random() * 10)).join('')
}

type Phase = 'ready' | 'showing' | 'input' | 'feedback'

export default function DigitSpan({ onComplete }: Props) {
  const [span,      setSpan]      = useState(3)
  const [sequence,  setSequence]  = useState('')
  const [showing,   setShowing]   = useState<number>(-1)   // index of digit being shown (-1 = between)
  const [typed,     setTyped]     = useState('')
  const [phase,     setPhase]     = useState<Phase>('ready')
  const [feedback,  setFeedback]  = useState<'correct' | 'wrong' | null>(null)
  const [best,      setBest]      = useState(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function startRound(currentSpan: number) {
    const seq = randDigits(currentSpan)
    setSequence(seq)
    setTyped('')
    setShowing(-1)
    setPhase('showing')
    // flash each digit: 800ms visible, 200ms blank
    let idx = 0
    function flashNext() {
      if (idx < seq.length) {
        setShowing(idx)
        timerRef.current = setTimeout(() => {
          setShowing(-1)
          timerRef.current = setTimeout(() => { idx++; flashNext() }, 200)
        }, 800)
      } else {
        setPhase('input')
      }
    }
    flashNext()
  }

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current) }, [])

  function handleSubmit() {
    const correct = typed === sequence
    setFeedback(correct ? 'correct' : 'wrong')
    setPhase('feedback')
    if (correct) {
      setBest(b => Math.max(b, span))
      if (span >= MAX_SPAN) { setTimeout(() => onComplete(span, MAX_SPAN), 1200) }
      else setTimeout(() => { setSpan(s => s + 1); startRound(span + 1) }, 1200)
    } else {
      setBest(b => Math.max(b, span - 1))
      setTimeout(() => onComplete(Math.max(0, span - 1), MAX_SPAN), 1500)
    }
  }

  const card: React.CSSProperties = {
    background: 'var(--surface)', border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius)', padding: '1.75rem', maxWidth: 560,
    width: '100%', margin: '0 auto', textAlign: 'center',
  }

  if (phase === 'ready') return (
    <div style={card}>
      <h3 style={{ marginBottom: '.75rem' }}>Digit Span</h3>
      <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.25rem' }}>
        Digits will flash one at a time. Type them back in the same order.
        Each correct answer increases the length by one.
      </p>
      <button className="btn-primary" onClick={() => startRound(span)}>Start →</button>
    </div>
  )

  if (phase === 'showing') return (
    <div style={card}>
      <div style={{ fontSize: '.8rem', color: 'var(--muted)', marginBottom: '1.5rem' }}>
        Span: {span} &nbsp;|&nbsp; Watch carefully
      </div>
      <div style={{
        fontSize: '5rem', fontWeight: 700, color: 'var(--brand)',
        height: '7rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
        letterSpacing: '0.05em',
      }}>
        {showing >= 0 ? sequence[showing] : ''}
      </div>
    </div>
  )

  if (phase === 'input') return (
    <div style={card}>
      <div style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: '1rem' }}>
        Type the {span} digits in order:
      </div>
      <input
        type="text"
        autoFocus
        inputMode="numeric"
        pattern="[0-9]*"
        maxLength={span}
        value={typed}
        onChange={e => setTyped(e.target.value.replace(/\D/g, '').slice(0, span))}
        onKeyDown={e => { if (e.key === 'Enter' && typed.length === span) handleSubmit() }}
        style={{
          fontSize: '2rem', textAlign: 'center', letterSpacing: '0.3em',
          width: 'min(100%, 280px)', height: 56, border: '2px solid var(--brand)',
          borderRadius: 10,
        }}
      />
      <button className="btn-primary" style={{ marginTop: '.75rem' }}
        onClick={handleSubmit} disabled={typed.length !== span}>
        Submit →
      </button>
    </div>
  )

  // feedback
  const ok = feedback === 'correct'
  return (
    <div style={card}>
      <div style={{ fontSize: '2.5rem' }}>{ok ? '✅' : '❌'}</div>
      <div style={{ fontSize: '1.1rem', fontWeight: 600, margin: '.5rem 0',
        color: ok ? 'var(--success)' : 'var(--danger)' }}>
        {ok ? `Correct! Moving to span ${span + 1}` : `The sequence was: ${sequence}`}
      </div>
      {!ok && <div style={{ color: 'var(--muted)', fontSize: '.85rem' }}>Best span: {best}</div>}
    </div>
  )
}
