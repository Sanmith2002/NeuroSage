import { useState, useCallback } from 'react'

interface Props { onComplete: (score: number, maxScore: number) => void }

const ROUNDS   = 10
const GRID_N   = 16   // 4×4

type Shape = { id: number; color: string; form: 'circle' | 'square' | 'triangle'; size: number; isOdd: boolean }

// Round configs: what is normal vs odd
const CONFIGS = [
  { normal: { color: '#4f6ef7', form: 'circle'   as const, size: 36 }, odd: { color: '#e53e3e', form: 'circle'   as const, size: 36 } },
  { normal: { color: '#4f6ef7', form: 'circle'   as const, size: 36 }, odd: { color: '#4f6ef7', form: 'square'   as const, size: 36 } },
  { normal: { color: '#38a169', form: 'square'   as const, size: 36 }, odd: { color: '#e53e3e', form: 'square'   as const, size: 36 } },
  { normal: { color: '#4f6ef7', form: 'circle'   as const, size: 36 }, odd: { color: '#4f6ef7', form: 'triangle' as const, size: 36 } },
  { normal: { color: '#9f7aea', form: 'circle'   as const, size: 36 }, odd: { color: '#9f7aea', form: 'circle'   as const, size: 22 } },
  { normal: { color: '#d97706', form: 'square'   as const, size: 34 }, odd: { color: '#4f6ef7', form: 'square'   as const, size: 34 } },
  { normal: { color: '#4f6ef7', form: 'triangle' as const, size: 36 }, odd: { color: '#e53e3e', form: 'triangle' as const, size: 36 } },
  { normal: { color: '#38a169', form: 'circle'   as const, size: 34 }, odd: { color: '#38a169', form: 'square'   as const, size: 34 } },
  { normal: { color: '#4f6ef7', form: 'circle'   as const, size: 36 }, odd: { color: '#4f6ef7', form: 'circle'   as const, size: 20 } },
  { normal: { color: '#9f7aea', form: 'square'   as const, size: 34 }, odd: { color: '#e53e3e', form: 'circle'   as const, size: 34 } },
]

function makeGrid(round: number): Shape[] {
  const cfg = CONFIGS[round % CONFIGS.length]
  const oddIdx = Math.floor(Math.random() * GRID_N)
  return Array.from({ length: GRID_N }, (_, i) => {
    if (i === oddIdx) return { id: i, ...cfg.odd, isOdd: true }
    return { id: i, ...cfg.normal, isOdd: false }
  })
}

function ShapeCell({ shape, onClick, revealed }: { shape: Shape; onClick: () => void; revealed: boolean }) {
  const highlight = revealed && shape.isOdd ? '#c6f6d5' : revealed && !shape.isOdd ? '#fff5f5' : 'transparent'
  const s = shape.size

  const inner = shape.form === 'circle' ? (
    <div style={{ width: s, height: s, borderRadius: '50%', background: shape.color }} />
  ) : shape.form === 'square' ? (
    <div style={{ width: s, height: s, borderRadius: 4, background: shape.color }} />
  ) : (
    // triangle via border trick
    <div style={{
      width: 0, height: 0,
      borderLeft: `${s/2}px solid transparent`,
      borderRight: `${s/2}px solid transparent`,
      borderBottom: `${s * 0.87}px solid ${shape.color}`,
    }} />
  )

  return (
    <button
      onClick={onClick}
      style={{
        width: 64, height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: highlight, border: '1px solid var(--border)', borderRadius: 8,
        cursor: revealed ? 'default' : 'pointer', transition: 'background .15s',
      }}
    >
      {inner}
    </button>
  )
}

export default function VisualSearch({ onComplete }: Props) {
  const [phase,   setPhase]   = useState<'ready' | 'playing' | 'done'>('ready')
  const [round,   setRound]   = useState(0)
  const [grid,    setGrid]    = useState<Shape[]>([])
  const [score,   setScore]   = useState(0)
  const [picked,  setPicked]  = useState<number | null>(null)   // index clicked

  const startGame = useCallback(() => {
    setRound(0); setScore(0); setPicked(null)
    setGrid(makeGrid(0))
    setPhase('playing')
  }, [])

  function handleClick(shape: Shape) {
    if (picked !== null) return
    setPicked(shape.id)
    const correct = shape.isOdd
    const newScore = correct ? score + 1 : score
    if (correct) setScore(newScore)

    setTimeout(() => {
      const nextRound = round + 1
      if (nextRound >= ROUNDS) {
        setPhase('done')
        onComplete(newScore, ROUNDS)
      } else {
        setRound(nextRound)
        setGrid(makeGrid(nextRound))
        setPicked(null)
      }
    }, 700)
  }

  const card: React.CSSProperties = {
    background: 'var(--surface)', border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius)', padding: '1.75rem', maxWidth: 560,
    width: '100%', margin: '0 auto',
  }

  if (phase === 'ready') return (
    <div style={card}>
      <h3 style={{ marginBottom: '.75rem' }}>Visual Search</h3>
      <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.25rem' }}>
        Click the shape that is <strong>different</strong> from the others in each grid.
        {' '}{ROUNDS} rounds total.
      </p>
      <button className="btn-primary" onClick={startGame}>Start →</button>
    </div>
  )

  if (phase === 'playing') {
    const lastCorrect  = picked !== null && grid.find(s => s.id === picked)?.isOdd
    return (
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', fontSize: '.85rem', color: 'var(--muted)' }}>
          <span>Round {round + 1} / {ROUNDS}</span>
          <span>Score: {score}</span>
        </div>
        {picked !== null && (
          <div style={{
            textAlign: 'center', marginBottom: '.75rem', fontWeight: 600,
            color: lastCorrect ? 'var(--success)' : 'var(--danger)',
            fontSize: '.9rem',
          }}>
            {lastCorrect ? '✓ Correct!' : '✗ That was not the odd one'}
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 64px)', gap: 6, margin: '0 auto', width: 'fit-content' }}>
          {grid.map(shape => (
            <ShapeCell key={shape.id} shape={shape} onClick={() => handleClick(shape)} revealed={picked !== null} />
          ))}
        </div>
        {picked === null && (
          <p style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '.8rem', marginTop: '.75rem' }}>
            Find and click the odd one out
          </p>
        )}
      </div>
    )
  }

  return (
    <div style={{ ...card, textAlign: 'center' }}>
      <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>
        {score} / {ROUNDS} correct
      </div>
    </div>
  )
}
