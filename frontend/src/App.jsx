import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'
import Layout from './components/Layout'

// Pages
import Home from './pages/Home'
import BriefingPage from './pages/BriefingPage'
import IdeasPage from './pages/IdeasPage'
import ExperimentsLivePage from './pages/ExperimentsLivePage'
import ExperimentDetail from './pages/ExperimentDetail'
import OpportunityDashboard from './pages/OpportunityDashboard'
import DailyOpportunityPage from './pages/DailyOpportunityPage'
import ManualIntelPage from './pages/ManualIntelPage'
import NotFound from './pages/NotFound'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/briefing/:date" element={<BriefingPage />} />
          <Route path="/daily-opportunities/:date" element={<DailyOpportunityPage />} />
          <Route path="/experiments/ideas" element={<IdeasPage />} />
          <Route path="/experiments/live" element={<ExperimentsLivePage />} />
          <Route path="/experiments/:id" element={<ExperimentDetail />} />
          <Route path="/opportunities/:date" element={<OpportunityDashboard />} />
          <Route path="/manual-intel" element={<ManualIntelPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
