import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DIAGNOSIS_PRESETS, NS_PROFILE_KEY, type Diagnosis, type NsProfile } from '../types'

interface FormErrors {
  name?: string
  age?: string
  education?: string
  diagnosis?: string
}

export default function ProfileSetup() {
  const navigate = useNavigate()

  const [name, setName]           = useState('')
  const [age, setAge]             = useState('')
  const [sex, setSex]             = useState<'M' | 'F' | ''>('')
  const [education, setEducation] = useState('')
  const [language, setLanguage]   = useState<'EN' | 'SI'>('EN')
  const [diagnosis, setDiagnosis] = useState<Diagnosis | ''>('')
  const [errors, setErrors]       = useState<FormErrors>({})

  function validate(): boolean {
    const e: FormErrors = {}
    if (!name.trim())                     e.name      = 'Please enter the patient name.'
    const ageNum = Number(age)
    if (!age || ageNum < 18 || ageNum > 100) e.age    = 'Age must be between 18 and 100.'
    const eduNum = Number(education)
    if (!education || eduNum < 0 || eduNum > 30) e.education = 'Education years must be 0–30.'
    if (!diagnosis)                       e.diagnosis = 'Please select a diagnosis.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function handleSubmit() {
    if (!validate()) return
    if (!diagnosis) return   // narrowing for TS

    const profile: NsProfile = {
      name: name.trim(),
      age: Number(age),
      sex: sex || 'M',
      education: Number(education),
      language,
      diagnosis,
      probabilities: DIAGNOSIS_PRESETS[diagnosis].probabilities,
    }

    try {
      localStorage.setItem(NS_PROFILE_KEY, JSON.stringify(profile))
    } catch {
      // localStorage unavailable — proceed anyway
    }

    navigate('/assess')
  }

  const isReady = name.trim() && age && sex && education && diagnosis

  return (
    <div className="page">

      {/* Header */}
      <div className="screen-header">
        <div className="logo">🧠 NeuroSage</div>
        <div className="subtitle">Cognitive Training System</div>
      </div>

      {/* Step dots: 1 of 5 active */}
      <div className="step-indicator">
        {[1,2,3,4,5].map(n => (
          <div key={n} className={`step-dot${n === 1 ? ' active' : ''}`} />
        ))}
      </div>

      {/* Form card */}
      <div className="card">
        <h2 style={{ marginBottom: '1.5rem', fontSize: '1.2rem' }}>Patient Profile</h2>

        {/* Name */}
        <div className="field">
          <label htmlFor="name">Full Name</label>
          <input
            id="name"
            type="text"
            placeholder="e.g. Kamal Perera"
            value={name}
            onChange={e => setName(e.target.value)}
          />
          {errors.name && <span className="field-error">{errors.name}</span>}
        </div>

        {/* Age */}
        <div className="field">
          <label htmlFor="age">Age <span className="hint">(years)</span></label>
          <input
            id="age"
            type="number"
            placeholder="e.g. 72"
            min={18}
            max={100}
            value={age}
            onChange={e => setAge(e.target.value)}
            style={{ maxWidth: 120 }}
          />
          {errors.age && <span className="field-error">{errors.age}</span>}
        </div>

        {/* Sex */}
        <div className="field">
          <label>Sex</label>
          <div className="toggle-group">
            {(['M', 'F'] as const).map(s => (
              <button
                key={s}
                className={`toggle-btn${sex === s ? ' selected' : ''}`}
                onClick={() => setSex(s)}
                type="button"
              >
                {s === 'M' ? 'Male' : 'Female'}
              </button>
            ))}
          </div>
        </div>

        {/* Education */}
        <div className="field">
          <label htmlFor="edu">
            Education <span className="hint">(years of formal schooling)</span>
          </label>
          <input
            id="edu"
            type="number"
            placeholder="e.g. 14"
            min={0}
            max={30}
            value={education}
            onChange={e => setEducation(e.target.value)}
            style={{ maxWidth: 120 }}
          />
          {errors.education && <span className="field-error">{errors.education}</span>}
        </div>

        {/* Language preference */}
        <div className="field">
          <label>Language Preference</label>
          <div className="toggle-group">
            <button
              className={`toggle-btn${language === 'EN' ? ' selected' : ''}`}
              onClick={() => setLanguage('EN')}
              type="button"
            >
              English
            </button>
            <button
              className={`toggle-btn${language === 'SI' ? ' selected' : ''}`}
              onClick={() => setLanguage('SI')}
              type="button"
            >
              සිංහල
            </button>
          </div>
        </div>

        <hr className="divider" />

        {/* Diagnosis */}
        <div className="field">
          <label htmlFor="diagnosis">Diagnosis</label>
          <select
            id="diagnosis"
            value={diagnosis}
            onChange={e => setDiagnosis(e.target.value as Diagnosis | '')}
            style={{
              height: 42, padding: '0 .875rem', borderRadius: 8,
              border: '1.5px solid var(--border)', fontSize: '.95rem',
              background: 'var(--surface)', color: diagnosis ? 'var(--text)' : 'var(--muted)',
              maxWidth: 400, width: '100%',
            }}
          >
            <option value="">Select a diagnosis…</option>
            {(Object.keys(DIAGNOSIS_PRESETS) as Diagnosis[]).map(key => (
              <option key={key} value={key}>{DIAGNOSIS_PRESETS[key].label}</option>
            ))}
          </select>
          {errors.diagnosis && <span className="field-error">{errors.diagnosis}</span>}
        </div>

        {/* Submit */}
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={!isReady}
          type="button"
        >
          Start Assessment →
        </button>
      </div>
    </div>
  )
}
