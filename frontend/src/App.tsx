import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import { ThemeProvider } from './contexts/ThemeContext'
import PublicLayout from './layouts/PublicLayout'
import AppLayout from './layouts/AppLayout'
import Home from './pages/Home'
import Compare from './pages/Compare'
import Pricing from './pages/Pricing'
import Contracts from './pages/Contracts'
import Settings from './pages/Settings'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import Disclaimer from './pages/Disclaimer'
import Admin from './pages/Admin'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [showLogin, setShowLogin] = useState(false)

  const handleLogin = () => {
    setIsLoggedIn(true)
    setShowLogin(false)
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
  }

  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          {isLoggedIn ? (
            <Route element={<AppLayout onLogout={handleLogout} />}>
              <Route path="/" element={<Home />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/contracts" element={<Contracts />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          ) : (
            <Route element={<PublicLayout onLoginClick={() => setShowLogin(true)} />}>
              <Route path="/" element={<Home />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/terms" element={<Terms />} />
              <Route path="/disclaimer" element={<Disclaimer />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          )}
        </Routes>

        {/* Login Modal Placeholder */}
        {showLogin && (
          <div className="modal-overlay" onClick={() => setShowLogin(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Welcome to SpotClause</h2>
                <button className="modal-close" onClick={() => setShowLogin(false)}>×</button>
              </div>
              <div className="modal-body">
                <div className="modal-left">
                  <h3>AI-Powered Contract Review</h3>
                  <ul>
                    <li>✓ Review contracts in seconds</li>
                    <li>✓ Identify hidden risks</li>
                    <li>✓ Get negotiation scripts</li>
                    <li>✓ Compare contract versions</li>
                  </ul>
                </div>
                <div className="modal-right">
                  <button className="btn btn-google" onClick={handleLogin}>
                    Continue with Google
                  </button>
                  <div className="divider">or</div>
                  <input type="email" placeholder="Email" className="input" />
                  <input type="password" placeholder="Password" className="input" />
                  <button className="btn btn-primary" onClick={handleLogin}>
                    Continue with Email
                  </button>
                  <p className="text-muted text-sm">
                    Don't have an account? <a href="#">Sign up</a>
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
