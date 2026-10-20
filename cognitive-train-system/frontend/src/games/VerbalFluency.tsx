import { useState, useEffect, useRef } from 'react'
import { NS_PROFILE_KEY, type NsProfile } from '../types'

interface Props { onComplete: (score: number, maxScore: number) => void }

const DURATION = 60
const MAX_SCORE = 30   // benchmark ceiling for display
const CATEGORIES = ['Animals', 'Fruits', 'Countries', 'Tools', 'Clothes']

// Speech recognition is browser-prefixed and untyped in the DOM libs.
type SpeechRec = {
  lang: string; continuous: boolean; interimResults: boolean
  start: () => void; stop: () => void
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
}
function getSpeechRecognition(): (new () => SpeechRec) | null {
  const w = window as unknown as { SpeechRecognition?: new () => SpeechRec; webkitSpeechRecognition?: new () => SpeechRec }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export default function VerbalFluency({ onComplete }: Props) {
  const [phase,    setPhase]    = useState<'ready' | 'playing' | 'done'>('ready')
  const [category, setCategory] = useState('')
  const [words,    setWords]    = useState<string[]>([])
  const [input,    setInput]    = useState('')
  const [timeLeft, setTimeLeft] = useState(DURATION)
  const [listening, setListening] = useState(false)

  const wordsRef = useRef<string[]>([])
  const doneRef  = useRef(false)
  const recRef   = useRef<SpeechRec | null>(null)

  const SR = getSpeechRecognition()
  const voiceSupported = !!SR

  // read patient language preference for the recogniser locale
  function recogLang(): string {
    try {
      const p = JSON.parse(localStorage.getItem(NS_PROFILE_KEY) ?? 'null') as NsProfile | null
      return p?.language === 'SI' ? 'si-LK' : 'en-US'
    } catch { return 'en-US' }
  }

  function addWord(raw: string) {
    const w = raw.trim().toLowerCase().replace(/[^a-z஀-௿඀-෿]/gi, '')
    if (!w || wordsRef.current.includes(w)) return
    wordsRef.current = [...wordsRef.current, w]
    setWords([...wordsRef.current])
  }

  function startGame() {
    const cat = CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)]
    setCategory(cat)
    setWords([]); wordsRef.current = []
    setInput('')
    setTimeLeft(DURATION)
    doneRef.current = false
    setPhase('playing')
  }

  // Countdown — one scheduled tick per second, NO side effects inside a state updater.
  useEffect(() => {
    if (phase !== 'playing') return
    if (timeLeft <= 0) {
      stopListening()
      setPhase('done')
      if (!doneRef.current) {
        doneRef.current = true
        onComplete(wordsRef.current.length, MAX_SCORE)
      }
      return
    }
    const id = setTimeout(() => setTimeLeft(t => t - 1), 1000)
    return () => clearTimeout(id)
  }, [phase, timeLeft])   // eslint-disable-line react-hooks/exhaustive-deps

  // Clean up the recogniser on unmount.
  useEffect(() => () => { try { recRef.current?.stop() } catch { /* ignore */ } }, [])

  function startListening() {
    if (!SR || listening) return
    const rec = new SR()
    rec.lang = recogLang()
    rec.continuous = true
    rec.interimResults = false
    rec.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          e.results[i][0].transcript.split(/\s+/).forEach(addWord)
        }
      }
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recRef.current = rec
    try { rec.start(); setListening(true) } catch { setListening(false) }
  }
  function stopListening() {
    try { recRef.current?.stop() } catch { /* ignore */ }
    setListening(false)
  }

  function submitTyped() {
    addWord(input)
    setInput('')
  }
  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); submitTyped() }
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
      <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1rem' }}>
        A category will appear. Say or type as many things in that category as you can in{' '}
        <strong>60 seconds</strong>.
      </p>
      <p style={{ color: 'var(--muted)', fontSize: '.82rem', marginBottom: '1.25rem' }}>
        {voiceSupported
          ? '🎙 Tap the mic to speak (recommended — this is a speaking task), or type and press Enter.'
          : 'Voice input is not available in this browser — type each word and press Enter.'}
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

      {/* Voice control */}
      {voiceSupported && (
        <button
          type="button"
          onClick={listening ? stopListening : startListening}
          style={{
            width: '100%', height: 46, marginBottom: '.6rem', borderRadius: 8, cursor: 'pointer',
            border: listening ? 'none' : '1.5px solid var(--brand)', fontWeight: 600, fontSize: '.9rem',
            background: listening ? 'var(--danger)' : 'var(--surface)',
            color: listening ? '#fff' : 'var(--brand)',
          }}
        >
          {listening ? '⏹ Stop listening' : '🎙 Speak words'}
        </button>
      )}

      {/* Typing fallback */}
      <div style={{ display: 'flex', gap: '.5rem' }}>
        <input
          autoFocus
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="…or type a word"
          style={{ flex: 1, height: 42, padding: '0 .875rem', borderRadius: 8, border: '1.5px solid var(--border)', fontSize: '.95rem' }}
        />
        <button className="btn-primary" style={{ width: 80, height: 42, marginTop: 0 }} onClick={submitTyped}>Add</button>
      </div>
      <div style={{ fontSize: '.75rem', color: 'var(--muted)', marginTop: '.4rem' }}>
        {words.length} word{words.length !== 1 ? 's' : ''} so far · duplicates ignored
        {listening && <span style={{ color: 'var(--danger)', fontWeight: 600 }}> · listening…</span>}
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
