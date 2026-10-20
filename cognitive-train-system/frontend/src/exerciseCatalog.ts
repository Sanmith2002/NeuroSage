// Task descriptions for the 15 catalog exercises (mirror of
// backend/models/exercise_catalog.json). Used to show the specific recommended
// exercise's real task in the player, even though each domain shares one game.
interface CatalogEntry { id: string; name: string; task: string }

export const EXERCISE_CATALOG: CatalogEntry[] = [
  // Memory
  { id: 'MEM-01', name: 'Spaced retrieval',       task: 'Recall target information over gradually expanding time intervals.' },
  { id: 'MEM-02', name: 'Errorless learning',     task: 'Relearn information while errors are prevented during encoding (cues given before any guess).' },
  { id: 'MEM-03', name: 'Sequence / list recall', task: 'Recall a sequence of items or everyday events in order after a delay.' },
  // Attention
  { id: 'ATT-01', name: 'Speed-of-processing / Useful Field of View', task: 'Rapidly identify and locate briefly shown targets across the visual field.' },
  { id: 'ATT-02', name: 'Cancellation / visual search',  task: 'Find and mark all target items among distractors; sustained and selective attention.' },
  { id: 'ATT-03', name: 'Digit span / divided attention', task: 'Hold and reproduce sequences, or respond to two streams at once.' },
  // Executive
  { id: 'EXE-01', name: 'n-back / working-memory updating', task: 'Indicate when the current item matches the one n steps earlier; continuous updating.' },
  { id: 'EXE-02', name: 'Task-switching / set-shifting',    task: 'Alternate between two rules or categories on cue; cognitive flexibility.' },
  { id: 'EXE-03', name: 'Planning / inhibition',            task: 'Plan a multi-step solution, or suppress a prepotent response (Stroop-type).' },
  // Language
  { id: 'LAN-01', name: 'Verbal fluency',                   task: 'Generate as many words as possible in a category or starting letter within a time limit.' },
  { id: 'LAN-02', name: 'Confrontation naming / word-finding', task: 'Name depicted objects or actions; retrieve the correct word under cueing if needed.' },
  { id: 'LAN-03', name: 'Semantic categorization / association', task: 'Sort words or pictures into categories, or match related concepts.' },
  // Visuospatial
  { id: 'VIS-01', name: 'Figure copying / construction',    task: 'Reproduce or assemble a geometric figure or arrangement from a model.' },
  { id: 'VIS-02', name: 'Mental rotation / spatial reasoning', task: 'Decide whether rotated shapes match; reason about spatial relations.' },
  { id: 'VIS-03', name: 'Visual search / spatial puzzle',   task: 'Locate targets by spatial layout, or complete a jigsaw / matching puzzle.' },
]

const norm = (s: string) => s.trim().toLowerCase()

// Resolve the task text by catalog id first, then by exercise name (case-insensitive).
export function exerciseTask(id?: string, name?: string): string | null {
  if (id) {
    const byId = EXERCISE_CATALOG.find(e => e.id === id)
    if (byId) return byId.task
  }
  if (name) {
    const byName = EXERCISE_CATALOG.find(e => norm(e.name) === norm(name))
    if (byName) return byName.task
  }
  return null
}
