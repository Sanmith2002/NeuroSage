// Central localStorage layer: patient registry, sessions, and tagged results.
// Name is the unique patient identity. Each "login" starts a new session so a
// patient's progress is kept and viewed per session, separate from other patients.
import { NS_PROFILE_KEY, type NsProfile } from './types'

const PATIENTS = 'ns_patients'
const ACTIVE   = 'ns_active'
const RESULTS  = 'ns_results'

export interface PatientRecord extends NsProfile {
  createdAt: string
  sessionCount: number
}

export interface Active {
  patientName: string
  sessionNo: number
}

export interface ResultRow {
  patientName: string
  sessionNo: number
  date: string
  domain: string
  exercise: string
  score: number
  maxScore: number
  pct: number
}

// ── low-level helpers ─────────────────────────────────────────────────────────
function readJSON<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    return v ? (JSON.parse(v) as T) : fallback
  } catch { return fallback }
}
function writeJSON(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* ignore */ }
}
const same = (a?: string, b?: string) =>
  (a ?? '').trim().toLowerCase() === (b ?? '').trim().toLowerCase()

// ── patient registry ──────────────────────────────────────────────────────────
export function listPatients(): PatientRecord[] {
  return readJSON<PatientRecord[]>(PATIENTS, [])
}
export function getPatient(name: string): PatientRecord | undefined {
  return listPatients().find(p => same(p.name, name))
}
export function patientExists(name: string): boolean {
  return !!getPatient(name)
}

// Create a brand-new patient and log in as Session 1.
export function createPatient(profile: NsProfile): PatientRecord {
  const patients = listPatients()
  const rec: PatientRecord = { ...profile, createdAt: new Date().toISOString(), sessionCount: 1 }
  patients.push(rec)
  writeJSON(PATIENTS, patients)
  setActive({ patientName: rec.name, sessionNo: 1 })
  writeActiveProfile(rec)
  restoreWorking(rec.name)   // fresh patient → clears any stray working keys
  return rec
}

// Open an existing patient → start a NEW session (sessionNo bumps).
export function loginPatient(name: string): Active | null {
  const patients = listPatients()
  const i = patients.findIndex(p => same(p.name, name))
  if (i < 0) return null
  patients[i].sessionCount += 1
  writeJSON(PATIENTS, patients)
  const active: Active = { patientName: patients[i].name, sessionNo: patients[i].sessionCount }
  setActive(active)
  writeActiveProfile(patients[i])
  restoreWorking(patients[i].name)   // bring back their saved assessment + plan
  return active
}

// Delete a patient and everything belonging to them.
export function deletePatient(name: string) {
  writeJSON(PATIENTS, listPatients().filter(p => !same(p.name, name)))
  writeJSON(RESULTS, readJSON<ResultRow[]>(RESULTS, []).filter(r => !same(r.patientName, name)))
  try {
    localStorage.removeItem(`ns_assess:${name}`)
    localStorage.removeItem(`ns_recommend:${name}`)
  } catch { /* ignore */ }
  const a = getActive()
  if (a && same(a.patientName, name)) endSession()
}

// ── active session ────────────────────────────────────────────────────────────
export function getActive(): Active | null {
  return readJSON<Active | null>(ACTIVE, null)
}
function setActive(a: Active) { writeJSON(ACTIVE, a) }

// Exit & Save: end the session but KEEP the patient and all their results.
export function endSession() {
  try {
    localStorage.removeItem(ACTIVE)
    localStorage.removeItem(NS_PROFILE_KEY)
    localStorage.removeItem('ns_assess')
    localStorage.removeItem('ns_recommend')
    localStorage.removeItem('ns_current_exercise')
  } catch { /* ignore */ }
}

function writeActiveProfile(p: PatientRecord) {
  const profile: NsProfile = {
    name: p.name, age: p.age, sex: p.sex, education: p.education,
    language: p.language, diagnosis: p.diagnosis, probabilities: p.probabilities,
  }
  writeJSON(NS_PROFILE_KEY, profile)
}

// ── per-patient assessment + plan persistence ─────────────────────────────────
export function saveAssessForActive(assess: unknown) {
  const a = getActive(); if (!a) return
  writeJSON(`ns_assess:${a.patientName}`, assess)
}
export function saveRecommendForActive(rec: unknown) {
  const a = getActive(); if (!a) return
  writeJSON(`ns_recommend:${a.patientName}`, rec)
}
export function hasSavedPlan(name: string): boolean {
  try { return !!localStorage.getItem(`ns_recommend:${name}`) } catch { return false }
}
// Copy a patient's saved assessment/plan into the working keys the flow reads.
function restoreWorking(name: string) {
  try {
    const as = localStorage.getItem(`ns_assess:${name}`)
    if (as) localStorage.setItem('ns_assess', as); else localStorage.removeItem('ns_assess')
    const rc = localStorage.getItem(`ns_recommend:${name}`)
    if (rc) localStorage.setItem('ns_recommend', rc); else localStorage.removeItem('ns_recommend')
    localStorage.removeItem('ns_current_exercise')
  } catch { /* ignore */ }
}

// ── results (tagged with active patient + session) ────────────────────────────
export function saveResult(row: Omit<ResultRow, 'patientName' | 'sessionNo' | 'date'>) {
  const a = getActive(); if (!a) return
  const results = readJSON<ResultRow[]>(RESULTS, [])
  results.push({ ...row, patientName: a.patientName, sessionNo: a.sessionNo, date: new Date().toISOString() })
  writeJSON(RESULTS, results)
}
export function getResults(name: string): ResultRow[] {
  return readJSON<ResultRow[]>(RESULTS, []).filter(r => same(r.patientName, name))
}

// One-time cleanup of duplicate rows produced by the old double-save bug
// (same patient/session/exercise/score logged within ~1.5s of each other).
export function cleanupDuplicateResults() {
  try {
    if (localStorage.getItem('ns_dedup_v1')) return
    const rows = readJSON<ResultRow[]>(RESULTS, [])
    const cleaned: ResultRow[] = []
    for (const r of rows) {
      const dup = cleaned.some(c =>
        same(c.patientName, r.patientName) && c.sessionNo === r.sessionNo &&
        c.exercise === r.exercise && c.score === r.score && c.maxScore === r.maxScore &&
        Math.abs(new Date(c.date).getTime() - new Date(r.date).getTime()) < 1500,
      )
      if (!dup) cleaned.push(r)
    }
    if (cleaned.length !== rows.length) writeJSON(RESULTS, cleaned)
    localStorage.setItem('ns_dedup_v1', '1')
  } catch { /* ignore */ }
}
