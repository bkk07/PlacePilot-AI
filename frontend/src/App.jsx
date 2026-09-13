import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import ApplicationsPage from './pages/ApplicationsPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import CompaniesPage from './pages/CompaniesPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import DriveDetailPage from './pages/DriveDetailPage.jsx'
import DriveWizardPage from './pages/DriveWizardPage.jsx'
import DrivesPage from './pages/DrivesPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import SignupPage from './pages/SignupPage.jsx'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="drives" element={<DrivesPage />} />
              <Route path="drives/:driveId" element={<DriveDetailPage />} />
              <Route path="profile" element={<ProtectedRoute roles={['student']}><ProfilePage /></ProtectedRoute>} />
              <Route path="applications" element={<ApplicationsPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="companies" element={<ProtectedRoute roles={['admin']}><CompaniesPage /></ProtectedRoute>} />
              <Route path="drives/new" element={<ProtectedRoute roles={['admin']}><DriveWizardPage /></ProtectedRoute>} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}