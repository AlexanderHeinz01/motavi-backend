import { BrowserRouter, Route, Routes } from 'react-router-dom'
import MarketingPage from './marketing/MarketingPage'
import AnalyzingPage from './pages/AnalyzingPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public marketing website */}
        <Route path="/" element={<MarketingPage />} />

        {/* Ergonomics analysis app */}
        <Route path="/app" element={<UploadPage />} />
        <Route path="/app/analyzing/:jobId" element={<AnalyzingPage />} />
        <Route path="/app/dashboard/:jobId" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  )
}
