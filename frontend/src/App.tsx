import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { HelmetProvider } from 'react-helmet-async'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import { useAuth } from './hooks/useAuth'
import { useToast } from './hooks/useToast'
import PublicLayout from './layouts/PublicLayout'
import AppLayout from './layouts/AppLayout'
import Home from './pages/Home'
import Compare from './pages/Compare'
import Pricing from './pages/Pricing'
import Contracts from './pages/Contracts'
import ContractReport from './pages/ContractReport'
import Settings from './pages/Settings'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import RefundPolicy from './pages/RefundPolicy'
import Disclaimer from './pages/Disclaimer'
import Admin from './pages/Admin'
import ToastViewport from './components/Toast'
import { authApi, api } from './lib/api'
import { supportedLanguages } from './i18n'

function AppContent() {
  const { t, i18n } = useTranslation()
  const { isLoggedIn, isReady, login, logout, showLogin, setShowLogin } = useAuth()
  const { showToast } = useToast()
  const [loginMode, setLoginMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [loading, setLoading] = useState(false)

  // IP-based language detection
  useEffect(() => {
    const savedLang = localStorage.getItem('spotclause-language')
    if (savedLang) return

    api.get('/api/pricing/detect')
      .then(res => {
        const countryCode = res.data.country_code
        const countryToLang: Record<string, string> = {
          US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en',
          DE: 'de', AT: 'de', CH: 'de',
          FR: 'fr', BE: 'fr', LU: 'fr', MC: 'fr',
          ES: 'es', MX: 'es', AR: 'es', CO: 'es', CL: 'es', PE: 'es', VE: 'es', EC: 'es', UY: 'es', PY: 'es', BO: 'es',
          PT: 'pt', BR: 'pt', AO: 'pt', MZ: 'pt',
          IT: 'it', SM: 'it', VA: 'it',
          TR: 'tr', CY: 'tr',
          TH: 'th',
          RU: 'ru', BY: 'ru', KZ: 'ru', KG: 'ru', TJ: 'ru',
          ID: 'id',
          JP: 'ja',
          KR: 'ko', KP: 'ko',
          TW: 'zh-TW', HK: 'zh-TW', MO: 'zh-TW',
          CN: 'zh-TW',
          SA: 'ar', AE: 'ar', EG: 'ar', QA: 'ar', KW: 'ar', BH: 'ar', OM: 'ar', JO: 'ar', LB: 'ar',
          IQ: 'ar', DZ: 'ar', MA: 'ar', TN: 'ar', LY: 'ar', SD: 'ar', SY: 'ar', YE: 'ar', PS: 'ar',
        }
        const detectedLang = countryToLang[countryCode] || 'en'
        if (detectedLang !== 'en') {
          i18n.changeLanguage(detectedLang)
          const lang = supportedLanguages.find(l => l.code === detectedLang)
          if (lang) {
            document.documentElement.dir = lang.dir
            document.documentElement.lang = detectedLang
          }
        }
      })
      .catch(() => {})
  }, [i18n])

  // Google Sign-In initialization
  useEffect(() => {
    authApi.getGoogleConfig()
      .then(res => {
        const clientId = res.data.client_id
        if (!clientId) return

        if (document.getElementById('google-gsi')) {
          initGoogle(clientId)
          return
        }

        const script = document.createElement('script')
        script.id = 'google-gsi'
        script.src = 'https://accounts.google.com/gsi/client'
        script.async = true
        script.defer = true
        script.onload = () => initGoogle(clientId)
        document.head.appendChild(script)
      })
      .catch(() => {})

    function initGoogle(clientId: string) {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: clientId,
          use_fedcm_for_prompt: false,
          callback: (response: { credential?: string }) => {
            if (response.credential) {
              handleGoogleCredential(response.credential)
            }
          },
        })
      }
    }
  }, [])

  const handleGoogleCredential = async (credential: string) => {
    try {
      setLoading(true)
      const res = await authApi.googleLogin(credential)
      login(res.data.access_token, res.data.user)
    } catch (err: any) {
      showToast(err.response?.data?.detail || t('common.loginFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt()
      return
    }

    // Development fallback when Google Client ID is not configured
    const mockToken = JSON.stringify({
      sub: 'google-' + Date.now(),
      email: `user${Date.now()}@example.com`,
      name: 'Test User',
      picture: null,
    })

    try {
      setLoading(true)
      const res = await authApi.googleLogin(mockToken)
      login(res.data.access_token, res.data.user)
    } catch (err: any) {
      showToast(err.response?.data?.detail || t('common.loginFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleEmailSubmit = async () => {
    if (!email || !password) {
      showToast(t('common.fillAllFields'), 'warning')
      return
    }

    if (loginMode === 'register' && !verificationCode) {
      showToast(t('auth.codeRequired'), 'warning')
      return
    }

    try {
      setLoading(true)

      if (loginMode === 'register') {
        const res = await authApi.register(email, password, verificationCode, name || undefined)
        login(res.data.access_token, res.data.user)
        showToast(t('auth.welcomeNew', { name: res.data.user.name || res.data.user.email }), 'success')
      } else {
        const res = await authApi.login(email, password)
        login(res.data.access_token, res.data.user)
        showToast(t('auth.welcomeBack', { name: res.data.user.name || res.data.user.email }), 'success')
      }

      setEmail('')
      setPassword('')
      setName('')
      setVerificationCode('')
      setCodeSent(false)
    } catch (err: any) {
      showToast(err.response?.data?.detail || t('common.authFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const sendVerificationCode = async () => {
    if (!email) {
      showToast(t('auth.emailRequired'), 'warning')
      return
    }
    if (!password) {
      showToast(t('auth.passwordRequired'), 'warning')
      return
    }

    try {
      setLoading(true)
      const res = await authApi.sendVerifyCode(email)
      setCodeSent(true)
      setCountdown(60)
      showToast(t('auth.codeSent'), 'success')
      if (res.data.code) {
        console.log('Debug verification code:', res.data.code)
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail || t('auth.codeSendFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  // Countdown timer for resend button
  useEffect(() => {
    if (countdown <= 0) return
    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [countdown])

  const resetForm = () => {
    setEmail('')
    setPassword('')
    setName('')
    setVerificationCode('')
    setCodeSent(false)
    setCountdown(0)
  }

  const openLoginModal = () => {
    resetForm()
    setLoginMode('login')
    setShowLogin(true)
  }

  const openRegisterModal = () => {
    resetForm()
    setLoginMode('register')
    setShowLogin(true)
  }

  if (!isReady) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="progress-spinner" />
      </div>
    )
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
            <Route path="/contracts/:id" element={<ContractReport />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/refund" element={<RefundPolicy />} />
            <Route path="/disclaimer" element={<Disclaimer />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        ) : (
          <Route element={<PublicLayout onLoginClick={openLoginModal} onRegisterClick={openRegisterModal} />}>
            <Route path="/" element={<Home />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/refund" element={<RefundPolicy />} />
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
                  <img src="/google-icon.svg" alt="" width="20" height="20" style={{ marginRight: '10px', flexShrink: 0 }} />
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

                {loginMode === 'register' && (
                  <div className="code-input-row">
                    <input
                      type="text"
                      inputMode="numeric"
                      placeholder={t('auth.verificationCode')}
                      className="input code-input"
                      value={verificationCode}
                      onChange={e => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      maxLength={6}
                    />
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={sendVerificationCode}
                      disabled={loading || countdown > 0}
                    >
                      {countdown > 0
                        ? t('auth.resendCode', { seconds: countdown })
                        : codeSent
                          ? t('auth.resend')
                          : t('auth.sendCode')}
                    </button>
                  </div>
                )}

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

      <ToastViewport />
    </BrowserRouter>
  )
}

function App() {
  return (
    <HelmetProvider>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <AppContent />
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </HelmetProvider>
  )
}

export default App
