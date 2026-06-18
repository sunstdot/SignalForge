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
import SearchPage from './pages/SearchPage'
import NotFound from './pages/NotFound'

// 静态部署模式：只有「情报搜索」可脱离后端工作，落地页与兜底都指向它
const STATIC = import.meta.env.VITE_STATIC_DATA === '1'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={STATIC ? <SearchPage /> : <Home />} />
          <Route path="/briefing/:date" element={<BriefingPage />} />
          <Route path="/daily-opportunities/:date" element={<DailyOpportunityPage />} />
          <Route path="/experiments/ideas" element={<IdeasPage />} />
          <Route path="/experiments/live" element={<ExperimentsLivePage />} />
          <Route path="/experiments/:id" element={<ExperimentDetail />} />
          <Route path="/opportunities/:date" element={<OpportunityDashboard />} />
          <Route path="/manual-intel" element={<ManualIntelPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="*" element={STATIC ? <SearchPage /> : <NotFound />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
