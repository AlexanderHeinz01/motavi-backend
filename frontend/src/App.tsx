import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import RequireBerater from './auth/RequireBerater'
import AnalyzingPage from './pages/AnalyzingPage'
import DashboardPage from './pages/DashboardPage'
import ExpertPage from './pages/ExpertPage'
import HochladenPage from './pages/HochladenPage'
import LoginPage from './pages/LoginPage'
import UploadPage from './pages/UploadPage'

/** Internal tool of the Motavi team plus the upload page for customers (G2 on 31.10.2026). */
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/hochladen/:token" element={<HochladenPage />} />

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
