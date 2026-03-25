import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Ontology from './pages/Ontology'
import Agents from './pages/Agents'
import Vibecoding from './pages/Vibecoding'
import Skills from './pages/Skills'
import MCP from './pages/MCP'
import Assets from './pages/Assets'
import Settings from './pages/Settings'
import Login from './pages/Login'
import DataManagement from './pages/DataManagement'
import Models from './pages/Models'
import Notifications from './components/Notifications'
import { ProtectedRoute, GuestRoute } from './components/ProtectedRoute'
import { useAuthStore } from './stores/authStore'
import OAuthCallback from './components/OAuthCallback'

function App() {
  const { loadUser, isLoading } = useAuthStore()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-500">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute>
              <Login />
            </GuestRoute>
          }
        />
        
        <Route
          path="/auth/oauth/callback/:provider"
          element={<OAuthCallback />}
        />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="ontology" element={<Ontology />} />
          <Route path="agents" element={<Agents />} />
          <Route path="vibecoding" element={<Vibecoding />} />
          <Route path="skills" element={<Skills />} />
          <Route path="mcp" element={<MCP />} />
          <Route path="assets" element={<Assets />} />
          <Route path="data" element={<DataManagement />} />
          <Route path="models" element={<Models />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Notifications />
    </BrowserRouter>
  )
}

export default App
