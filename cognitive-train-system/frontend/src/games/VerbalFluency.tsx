import { useState, useEffect, useRef } from 'react'

interface Props { onComplete: (score: number, maxScore: number) => void }

const DURATION = 60
const MAX_SCORE = 30   // benchmark ceiling for display
const CATEGORIES = ['Animals', 'Fruits', 'Countries', 'Tools', 'Clothes']

export default function VerbalFluency({ onComplete }: Props) {
  const [phase,    setPhase]   = useState<'ready' | 'playing' | 'done'>('ready')
  const [category, setCategory] = useState('')
  const [words,    setWords]   = useState<string[]>([])
  const [input,    setInput]   = useState('')
  const [timeLeft, setTimeLeft] = useState(DURATION)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const wordsRef = useRef<string[]>([])

  function startGame() {
    const cat = CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)]
    setCategory(cat)
    setWords([]); wordsRef.current = []
    setInput('')
    setTimeLeft(DURATION)
    setPhase('playing')
  }

  useEffect(() => {
    if (phase !== 'playing') return
    timerRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(timerRef.current!)
          setPhase('done')
          onComplete(wordsRef.current.length, MAX_SCORE)
          return 0
        }
        return t - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current!)
  }, [phase])

  function addWord() {
    const w = input.trim().toLowerCase()
    if (!w || wordsRef.current.includes(w)) { setInput(''); return }
    wordsRef.current = [...wordsRef.current, w]
    setWords([...wordsRef.current])
    setInput('')
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addWord() }
  }

  const card: React.CSSProperties = {
    background: 'var(--surface)', border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius)', padding: '1.75rem', maxWidth: 560,
    width: '100%', margin: '0 auto',
  }
  const timePct = (timeLeft / DURATION) * 100
  const barColor = timeLeft > 20 ? 'var(--brand)' : timeLeft > 10 ? '#d97706' : 'var(--danger)'

  if (phase === 'ready') return (
    <div style={card}>
      <h3 style={{ marginBottom: '.75rem' }}>Verbal Fluency</h3>
      <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.25rem' }}>
        A category will appear. Type as many things in that category as you can in{' '}
        <strong>60 seconds</strong>. Press <kbd style={{ background: 'var(--bg)', padding: '0 .4rem', borderRadius: 4 }}>Enter</kbd>{' '}
        after each word.
      </p>
      <button className="btn-primary" onClick={startGame}>Start →</button>
    </div>
  )

  if (phase === 'playing') return (
    <div style={card}>
      {/* Category + timer */}
      <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
        <div style={{ fontSize: '.78rem', color: 'var(--muted)' }}>Category</div>
        <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--brand)' }}>{category}</div>
      </div>

      {/* Countdown bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '.75rem', marginBottom: '1rem' }}>
        <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--border)' }}>
          <div style={{ height: '100%', borderRadius: 4, background: barColor, width: `${timePct}%`, transition: 'width 1s linear, background .5s' }} />
        </div>
        <span style={{ fontWeight: 700, color: barColor, minWidth: 28, textAlign: 'right' }}>{timeLeft}s</span>
      </div>

      {/* Word chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem', minHeight: 40, marginBottom: '1rem' }}>
        {words.map(w => (
          <span key={w} style={{
            padding: '.25rem .65rem', borderRadius: 20,
            background: '#eef1fe', color: 'var(--brand)', fontSize: '.85rem', fontWeight: 600,
          }}>{w}</span>
        ))}
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: '.5rem' }}>
        <input
          autoFocus
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Type a word…"
          style={{ flex: 1, height: 42, padding: '0 .875rem', borderRadius: 8, border: '1.5px solid var(--border)', fontSize: '.95rem' }}
        />
        <button className="btn-primary" style={{ width: 80, height: 42, marginTop: 0 }} onClick={addWord}>Add</button>
      </div>
      <div style={{ fontSize: '.75rem', color: 'var(--muted)', marginTop: '.4rem' }}>
        {words.length} word{words.length !== 1 ? 's' : ''} so far · duplicates ignored
      </div>
    </div>
  )

  return (
    <div style={{ ...card, textAlign: 'center' }}>
      <div style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '.5rem' }}>
        {words.length} unique words in {category}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem', justifyContent: 'center', marginTop: '.75rem' }}>
        {words.map(w => (
          <span key={w} style={{ padding: '.25rem .65rem', borderRadius: 20, background: '#eef1fe', color: 'var(--brand)', fontSize: '.85rem' }}>{w}</span>
        ))}
      </div>
    </div>
  )
}
