import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AnalyzingPage from './pages/AnalyzingPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/analyzing/:jobId" element={<AnalyzingPage />} />
        <Route path="/dashboard/:jobId" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  )
}
