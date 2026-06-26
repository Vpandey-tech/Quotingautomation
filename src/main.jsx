import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App.jsx'
import Landing from './pages/Landing.jsx'
import DesignDashboard from './pages/DesignDashboard.jsx'
import DesignSession from './pages/DesignSession.jsx'
import Login from './pages/Login.jsx'
import './index.css'

function ProtectedRoute({ children }) {
  const isAuthenticated = localStorage.getItem('accu_auth') === 'true';
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><Landing /></ProtectedRoute>} />
        <Route path="/quote" element={<ProtectedRoute><App /></ProtectedRoute>} />
        <Route path="/design" element={<ProtectedRoute><DesignDashboard /></ProtectedRoute>} />
        <Route path="/design/session/:id" element={<ProtectedRoute><DesignSession /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
