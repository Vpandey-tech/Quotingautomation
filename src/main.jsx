import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import Landing from './pages/Landing.jsx'
import DesignDashboard from './pages/DesignDashboard.jsx'
import DesignSession from './pages/DesignSession.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/quote" element={<App />} />
        <Route path="/design" element={<DesignDashboard />} />
        <Route path="/design/session/:id" element={<DesignSession />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
