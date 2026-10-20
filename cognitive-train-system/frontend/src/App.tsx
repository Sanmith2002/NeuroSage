import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing'
import ProfileSetup from './pages/ProfileSetup'
import Assessment from './pages/Assessment'
import Recommendation from './pages/Recommendation'
import ExercisePlayer from './pages/ExercisePlayer'
import Progress from './pages/Progress'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/new" element={<ProfileSetup />} />
        <Route path="/assess" element={<Assessment />} />
        <Route path="/recommend" element={<Recommendation />} />
        <Route path="/exercise" element={<ExercisePlayer />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
