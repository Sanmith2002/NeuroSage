import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DIAGNOSIS_PRESETS } from '../types'
import { listPatients, loginPatient, deletePatient, hasSavedPlan, type PatientRecord } from '../storage'

export default function Landing() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<PatientRecord[]>(() => listPatients())

  function openPatient(p: PatientRecord) {
    loginPatient(p.name)
    // Returning patient with a saved plan → straight to their plan; otherwise assess.
    navigate(hasSavedPlan(p.name) ? '/recommend' : '/assess')
  }

  function removePatient(p: PatientRecord) {
    if (!window.confirm(`Delete ${p.name} and all their session history? This cannot be undone.`)) return
    deletePatient(p.name)
    setPatients(listPatients())
  }

  return (
    <div className="page">
      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">Cognitive Training System</div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.2rem' }}>Patient Profiles</h2>
          <button
            className="btn-primary"
            style={{ width: 'auto', marginTop: 0, padding: '.5rem 1rem', fontSize: '.88rem' }}
            onClick={() => navigate('/new')}
          >
            ＋ New Patient
          </button>
        </div>

        {patients.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--muted)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '.5rem' }}>👤</div>
            <p style={{ fontSize: '.9rem', marginBottom: '1.25rem' }}>
              No patients yet. Add one to begin.
            </p>
            <button className="btn-primary" style={{ maxWidth: 260, margin: '0 auto' }} onClick={() => navigate('/new')}>
              ＋ Add First Patient
            </button>
          </div>
        ) : (
          patients.map(p => (
            <div
              key={p.name}
              style={{
                display: 'flex', alignItems: 'center', gap: '.75rem',
                padding: '.9rem 0', borderBottom: '1px solid var(--border)',
              }}
            >
              <div style={{
                width: 42, height: 42, borderRadius: '50%', background: '#eef1fe',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand)', flexShrink: 0,
              }}>
                {p.name.trim().charAt(0).toUpperCase()}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: '.95rem' }}>{p.name}</div>
                <div style={{ fontSize: '.76rem', color: 'var(--muted)', marginTop: '.1rem' }}>
                  Age {p.age} · {DIAGNOSIS_PRESETS[p.diagnosis]?.label ?? p.diagnosis} ·{' '}
                  {p.sessionCount} session{p.sessionCount !== 1 ? 's' : ''}
                </div>
              </div>

              <button
                onClick={() => openPatient(p)}
                style={{
                  padding: '.45rem .9rem', borderRadius: 8, border: 'none',
                  background: 'var(--brand)', color: '#fff', fontWeight: 600,
                  fontSize: '.82rem', cursor: 'pointer', flexShrink: 0,
                }}
              >
                Open →
              </button>
              <button
                onClick={() => removePatient(p)}
                title={`Delete ${p.name}`}
                style={{
                  padding: '.45rem .6rem', borderRadius: 8, border: '1.5px solid var(--border)',
                  background: 'var(--surface)', color: 'var(--danger)', fontSize: '.82rem',
                  cursor: 'pointer', flexShrink: 0,
                }}
              >
                🗑
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
