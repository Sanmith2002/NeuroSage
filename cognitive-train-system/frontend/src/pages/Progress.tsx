import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getActive, getResults, endSession, type ResultRow } from '../storage'

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
const avg = (rows: ResultRow[]) =>
  rows.length ? Math.round(rows.reduce((s, r) => s + r.pct, 0) / rows.length) : 0

// ── Main chart: average % per session (shows improvement over time) ───────────
const CHART_H = 150
function SessionTrend({ sessions, current }: { sessions: { no: number; rows: ResultRow[] }[]; current: number }) {
  return (
    <div>
      {/* bars share a common baseline */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '.6rem', height: CHART_H, padding: '0 .25rem' }}>
        {sessions.map(s => {
          const a = avg(s.rows)
          const isCur = s.no === current
          return (
            <div key={s.no} style={{ flex: 1, height: CHART_H, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center' }}>
              <span style={{ fontSize: '.72rem', fontWeight: 700, color: pctColor(a), marginBottom: '.2rem' }}>{a}%</span>
              <div style={{
                width: '100%', maxWidth: 48, height: `${Math.max(3, a)}%`,
                minHeight: 4, borderRadius: '6px 6px 0 0', background: pctColor(a),
                opacity: isCur ? 1 : 0.5, transition: 'height .4s',
                border: isCur ? '2px solid var(--brand)' : 'none', boxSizing: 'border-box',
              }} />
            </div>
          )
        })}
      </div>
      {/* baseline labels */}
      <div style={{ display: 'flex', gap: '.6rem', padding: '.35rem .25rem 0', borderTop: '1px solid var(--border)' }}>
        {sessions.map(s => (
          <span key={s.no} style={{
            flex: 1, textAlign: 'center', fontSize: '.72rem',
            color: s.no === current ? 'var(--brand)' : 'var(--muted)', fontWeight: s.no === current ? 700 : 500,
          }}>
            S{s.no}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Per-session detail: one bar per exercise played that session ──────────────
function SessionDetail({ rows }: { rows: ResultRow[] }) {
  return (
    <div style={{ padding: '.75rem .25rem .25rem' }}>
      {rows.map((r, i) => (
        <div key={i} style={{ marginBottom: '.7rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.82rem', marginBottom: '.25rem' }}>
            <span style={{ fontWeight: 600 }}>
              {DOMAIN_ICONS[r.domain] ?? '🔬'} {r.exercise}
              <span style={{ color: 'var(--muted)', fontWeight: 400 }}> · {DOMAIN_LABELS[r.domain] ?? r.domain}</span>
            </span>
            <span style={{ fontWeight: 700, color: pctColor(r.pct) }}>{r.score}/{r.maxScore} ({r.pct}%)</span>
          </div>
          <div style={{ height: 7, borderRadius: 4, background: 'var(--border)' }}>
            <div style={{ height: '100%', borderRadius: 4, width: `${r.pct}%`, background: DOMAIN_COLORS[r.domain] ?? 'var(--brand)' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Progress() {
  const navigate = useNavigate()
  const active = getActive()
  const [openSession, setOpenSession] = useState<number | null>(null)

  // No active patient → back to profiles.
  if (!active) {
    return (
      <div className="page">
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>No patient is signed in.</p>
          <button className="btn-primary" onClick={() => navigate('/')}>Go to Patient Profiles</button>
        </div>
      </div>
    )
  }

  const name = active.patientName
  const results = getResults(name)

  // group by session number, ascending
  const bySession = new Map<number, ResultRow[]>()
  for (const r of results) {
    if (!bySession.has(r.sessionNo)) bySession.set(r.sessionNo, [])
    bySession.get(r.sessionNo)!.push(r)
  }
  const sessions = [...bySession.entries()]
    .map(([no, rows]) => ({ no, rows }))
    .sort((a, b) => a.no - b.no)

  // overall per-domain averages across all sessions
  const byDomain: Record<string, ResultRow[]> = {}
  for (const r of results) (byDomain[r.domain] ??= []).push(r)
  const domains = Object.keys(byDomain).sort()

  function exitAndSave() {
    endSession()
    navigate('/')
  }

  return (
    <div className="page">
      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">{name} · Session {active.sessionNo}</div>
      </div>

      <div className="step-indicator">
        {[1, 2, 3, 4, 5].map(n => (
          <div key={n} className={`step-dot${n === 5 ? ' active' : ''}`} />
        ))}
      </div>

      {sessions.length === 0 ? (
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '.75rem' }}>📊</div>
          <h2 style={{ marginBottom: '.5rem' }}>No exercises yet</h2>
          <p style={{ color: 'var(--muted)', fontSize: '.88rem', marginBottom: '1.25rem' }}>
            Play an exercise this session to start building {name}'s progress.
          </p>
          <button className="btn-primary" onClick={() => navigate('/recommend')}>Go to Exercise Plan →</button>
        </div>
      ) : (
        <>
          {/* Main progress chart */}
          <div className="card">
            <h2 style={{ fontSize: '1.1rem', marginBottom: '.25rem' }}>Progress Over Sessions</h2>
            <p style={{ fontSize: '.78rem', color: 'var(--muted)', marginBottom: '1rem' }}>
              Average score per session · current session outlined
            </p>
            <SessionTrend sessions={sessions} current={active.sessionNo} />
          </div>

          {/* Overall per-domain averages */}
          <div className="card">
            <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Overall by Domain</h2>
            {domains.map(d => {
              const a = avg(byDomain[d])
              return (
                <div key={d} style={{ display: 'flex', alignItems: 'center', gap: '.75rem', marginBottom: '.75rem' }}>
                  <span style={{ width: 24, textAlign: 'center' }}>{DOMAIN_ICONS[d] ?? '🔬'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '.2rem' }}>
                      <span style={{ fontSize: '.85rem', fontWeight: 600 }}>{DOMAIN_LABELS[d] ?? d}</span>
                      <span style={{ fontSize: '.82rem', color: pctColor(a), fontWeight: 700 }}>
                        {a}% · {byDomain[d].length}×
                      </span>
                    </div>
                    <div style={{ height: 7, borderRadius: 4, background: 'var(--border)' }}>
                      <div style={{ height: '100%', borderRadius: 4, width: `${a}%`, background: DOMAIN_COLORS[d] ?? 'var(--brand)' }} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Session list — click to reveal that session's chart */}
          <div className="card">
            <h2 style={{ fontSize: '1.1rem', marginBottom: '.25rem' }}>Sessions</h2>
            <p style={{ fontSize: '.78rem', color: 'var(--muted)', marginBottom: '.75rem' }}>
              Tap a session to see its exercises
            </p>
            {[...sessions].reverse().map(s => {
              const a = avg(s.rows)
              const open = openSession === s.no
              const isCur = s.no === active.sessionNo
              return (
                <div key={s.no} style={{ borderBottom: '1px solid var(--border)' }}>
                  <button
                    onClick={() => setOpenSession(open ? null : s.no)}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '.75rem',
                      padding: '.85rem 0', background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left',
                    }}
                  >
                    <span style={{ fontSize: '.8rem', transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .2s', color: 'var(--muted)' }}>▶</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '.9rem' }}>
                        Session {s.no}{isCur && <span style={{ color: 'var(--brand)', fontWeight: 700 }}> · current</span>}
                      </div>
                      <div style={{ fontSize: '.74rem', color: 'var(--muted)', marginTop: '.1rem' }}>
                        {s.rows.length} exercise{s.rows.length !== 1 ? 's' : ''} · {formatDate(s.rows[0].date)}
                      </div>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '.95rem', color: pctColor(a) }}>{a}%</span>
                  </button>
                  {open && <SessionDetail rows={s.rows} />}
                </div>
              )
            })}
          </div>

          {/* Actions */}
          <button className="btn-primary" onClick={() => navigate('/recommend')} style={{ maxWidth: 560, width: '100%' }}>
            Back to Exercise Plan →
          </button>
          <button
            onClick={exitAndSave}
            style={{
              maxWidth: 560, width: '100%', marginTop: '.6rem', height: 46, borderRadius: 'var(--radius)',
              border: '1.5px solid var(--border)', background: 'var(--surface)', color: 'var(--text)',
              fontWeight: 600, fontSize: '.92rem', cursor: 'pointer',
            }}
          >
            Exit &amp; Save → Patient Profiles
          </button>
        </>
      )}
    </div>
  )
}
