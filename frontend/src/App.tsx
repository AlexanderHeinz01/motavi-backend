import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import RequireBerater from './auth/RequireBerater'
import MarketingPage from './marketing/MarketingPage'
import AnalyzingPage from './pages/AnalyzingPage'
import DashboardPage from './pages/DashboardPage'
import ExpertPage from './pages/ExpertPage'
import LoginPage from './pages/LoginPage'
import UploadPage from './pages/UploadPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/" element={<MarketingPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected ergonomics analysis app */}
          <Route path="/app" element={<RequireAuth><UploadPage /></RequireAuth>} />
          <Route path="/app/analyzing/:jobId" element={<RequireAuth><AnalyzingPage /></RequireAuth>} />
          <Route path="/app/dashboard/:jobId" element={<RequireAuth><DashboardPage /></RequireAuth>} />

          {/* Expert view: process steps, only for consultants */}
          <Route path="/app/experte/:jobId" element={<RequireBerater><ExpertPage /></RequireBerater>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
