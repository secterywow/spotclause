import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
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
import { authApi } from './lib/api'

function AppContent() {
  const { t } = useTranslation()
  const { isLoggedIn, isAdmin, login, logout } = useAuth()
  const [showLogin, setShowLogin] = useState(false)
  const [loginMode, setLoginMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleGoogleLogin = async () => {
    // TODO: Integrate with Google OAuth
    // For now, simulate login with a mock token
    const mockToken = JSON.stringify({
      sub: 'google-123',
      email: 'user@example.com',
      name: 'Test User',
      picture: null,
    })

    try {
      setLoading(true)
      const res = await authApi.googleLogin(mockToken)
      login(res.data.access_token, res.data.user)
      setShowLogin(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleEmailSubmit = async () => {
    if (!email || !password) {
      setError('Please fill in all fields')
      return
    }

    try {
      setLoading(true)
      setError('')

      if (loginMode === 'register') {
        const res = await authApi.register(email, password, name || undefined)
        login(res.data.access_token, res.data.user)
      } else {
        const res = await authApi.login(email, password)
        login(res.data.access_token, res.data.user)
      }

      setShowLogin(false)
      setEmail('')
      setPassword('')
      setName('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setError('')
    setEmail('')
    setPassword('')
    setName('')
  }

  return (
    <BrowserRouter>
      <Routes>
        {isLoggedIn ? (
          <Route element={<AppLayout onLogout={logout} />}>
            <Route path="/" element={<Home />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/contracts" element={<Contracts />} />
            <Route path="/settings" element={<Settings />} />
            {isAdmin && <Route path="/admin" element={<Admin />} />}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        ) : (
          <Route element={<PublicLayout onLoginClick={() => { resetForm(); setShowLogin(true); }} />}>
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

      {/* Login Modal */}
      {showLogin && (
        <div className="modal-overlay" onClick={() => setShowLogin(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('auth.welcome')}</h2>
              <button className="modal-close" onClick={() => setShowLogin(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="modal-left">
                <h3>{t('auth.tagline')}</h3>
                <ul>
                  <li>✓ {t('auth.feature1')}</li>
                  <li>✓ {t('auth.feature2')}</li>
                  <li>✓ {t('auth.feature3')}</li>
                  <li>✓ {t('auth.feature4')}</li>
                </ul>
              </div>
              <div className="modal-right">
                <button className="btn btn-google" onClick={handleGoogleLogin} disabled={loading}>
                  {t('auth.continueGoogle')}
                </button>
                <div className="divider">{t('common.or')}</div>

                {loginMode === 'register' && (
                  <input
                    type="text"
                    placeholder="Name (optional)"
                    className="input"
                    value={name}
                    onChange={e => setName(e.target.value)}
                  />
                )}
                <input
                  type="email"
                  placeholder={t('auth.email')}
                  className="input"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
                <input
                  type="password"
                  placeholder={t('auth.password')}
                  className="input"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />

                {error && <p className="text-error">{error}</p>}

                <button className="btn btn-primary" onClick={handleEmailSubmit} disabled={loading}>
                  {loading ? t('common.loading') : loginMode === 'login' ? t('auth.continueEmail') : t('common.submit')}
                </button>

                <p className="text-muted text-sm">
                  {loginMode === 'login' ? (
                    <>
                      {t('auth.noAccount')} <a href="#" onClick={(e) => { e.preventDefault(); setLoginMode('register'); resetForm(); }}>{t('auth.signUp')}</a>
                    </>
                  ) : (
                    <>
                      Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); setLoginMode('login'); resetForm(); }}>{t('auth.login')}</a>
                    </>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </BrowserRouter>
  )
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
