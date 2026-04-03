import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'

// Pages
import Home from './pages/Home'
import BriefingPage from './pages/BriefingPage'
import IdeasPage from './pages/IdeasPage'
import ExperimentsLivePage from './pages/ExperimentsLivePage'
import ExperimentDetail from './pages/ExperimentDetail'
import NotFound from './pages/NotFound'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/briefing/:date" element={<BriefingPage />} />
        <Route path="/experiments/ideas" element={<IdeasPage />} />
        <Route path="/experiments/live" element={<ExperimentsLivePage />} />
        <Route path="/experiments/:id" element={<ExperimentDetail />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  )
}

export default App
