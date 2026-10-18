import { useState, useEffect, useRef } from 'react'

interface Props { onComplete: (score: number, maxScore: number) => void }

const LETTERS   = 'BCDFGHJKLMNPQRSTVWXYZ'.split('')
const N         = 2
const TRIALS    = 20
const DISPLAY_MS = 2000   // how long each letter shows

function randLetter() { return LETTERS[Math.floor(Math.random() * LETTERS.length)] }

function buildSequence(len: number) {
  const seq = Array.from({ length: len }, randLetter)
  // inject ~30% targets (positions where seq[i] === seq[i-N])
  for (let i = N; i < len; i++) {
    if (Math.random() < 0.3) seq[i] = seq[i - N]
  }
  return seq
}

type Phase = 'ready' | 'playing' | 'done'

export default function NBack({ onComplete }: Props) {
  const [phase,    setPhase]   = useState<Phase>('ready')
  const [sequence, setSequence] = useState<string[]>([])
  const [idx,      setIdx]     = useState(0)
  const [hits,     setHits]    = useState(0)   // correct Match presses
  const [misses,   setMisses]  = useState(0)   // missed targets
  const [fas,      setFas]     = useState(0)   // false alarms
  const [pressed,  setPressed] = useState(false)
  const [flash,    setFlash]   = useState<'hit' | 'miss' | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const seqRef   = useRef<string[]>([])
  const idxRef   = useRef(0)
  const hitsRef  = useRef(0)
  const missRef  = useRef(0)
  const fasRef   = useRef(0)
  const pressedRef = useRef(false)

  function startGame() {
    const seq = buildSequence(TRIALS)
    seqRef.current   = seq
    idxRef.current   = 0
    hitsRef.current  = 0
    missRef.current  = 0
    fasRef.current   = 0
    pressedRef.current = false
    setSequence(seq)
    setIdx(0); setHits(0); setMisses(0); setFas(0); setPressed(false); setFlash(null)
    setPhase('playing')

    timerRef.current = setInterval(() => {
      const cur = idxRef.current
      // score previous trial before advancing
      const isTarget = cur >= N && seqRef.current[cur] === seqRef.current[cur - N]
      if (!pressedRef.current && isTarget) { missRef.current++; setMisses(missRef.current) }

      pressedRef.current = false
      setPressed(false)
      setFlash(null)

      const next = cur + 1
      if (next >= seqRef.current.length) {
        clearInterval(timerRef.current!)
        setPhase('done')
        onComplete(hitsRef.current, missRef.current + hitsRef.current || 1)
        return
      }
      idxRef.current = next
      setIdx(next)
    }, DISPLAY_MS)
  }

  useEffect(() => () => { clearInterval(timerRef.current!) }, [])

  function handleMatch() {
    if (pressed) return
    const cur = idxRef.current
    const isTarget = cur >= N && seqRef.current[cur] === seqRef.current[cur - N]
    pressedRef.current = true
    setPressed(true)
    if (isTarget) {
      hitsRef.current++; setHits(hitsRef.current)
      setFlash('hit')
    } else {
      fasRef.current++; setFas(fasRef.current)
      setFlash('miss')
    }
  }

  const card: React.CSSProperties = {
    background: 'var(--surface)', border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius)', padding: '1.75rem', maxWidth: 560,
    width: '100%', margin: '0 auto', textAlign: 'center',
  }

  if (phase === 'ready') return (
    <div style={card}>
      <h3 style={{ marginBottom: '.75rem' }}>2-Back</h3>
      <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '.75rem' }}>
        Letters appear one at a time. Press <strong>"Match"</strong> when the current letter
        is the same as the one that appeared <strong>2 steps ago</strong>.
      </p>
      <p style={{ fontSize: '.82rem', color: 'var(--muted)', marginBottom: '1.25rem' }}>
        Example: B → <u>C</u> → B ← press Match here
      </p>
      <button className="btn-primary" onClick={startGame}>Start ({TRIALS} trials) →</button>
    </div>
  )

  if (phase === 'playing') {
    const bgLetter = flash === 'hit' ? '#c6f6d5' : flash === 'miss' ? '#fed7d7' : 'var(--bg)'
    return (
      <div style={card}>
        <div style={{ fontSize: '.78rem', color: 'var(--muted)', marginBottom: '1rem' }}>
          Trial {idx + 1} / {TRIALS} &nbsp;·&nbsp; Hits: {hits} &nbsp;·&nbsp; Misses: {misses}
        </div>
        <div style={{
          width: 120, height: 120, borderRadius: 16, margin: '0 auto 1.5rem',
          background: bgLetter, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '4rem', fontWeight: 700, color: 'var(--brand)',
          transition: 'background .15s', border: '2px solid var(--border)',
        }}>
          {sequence[idx]}
        </div>
        <button
          className="btn-primary"
          onClick={handleMatch}
          disabled={pressed}
          style={{ fontSize: '1.1rem', height: 52 }}
        >
          {pressed ? (flash === 'hit' ? '✓ Matched!' : '✗ Wrong') : 'Match'}
        </button>
      </div>
    )
  }

  // done
  const targets = missRef.current + hitsRef.current
  const acc = targets > 0 ? Math.round((hitsRef.current / targets) * 100) : 0
  return (
    <div style={card}>
      <div style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '.5rem' }}>
        Accuracy: {acc}%
      </div>
      <div style={{ color: 'var(--muted)', fontSize: '.85rem' }}>
        Hits {hitsRef.current} · Missed {missRef.current} · False alarms {fasRef.current}
      </div>
    </div>
  )
}
