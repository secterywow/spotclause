import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { api } from '../lib/api'
import SEOContent from '../components/SEOContent'
import UserGreeting from '../components/UserGreeting'
import SubscriptionModal from '../components/SubscriptionModal'
import CompareResult, { type CompareReport } from '../components/CompareResult'

const COMPARE_STEPS = 6

function CompareProgress({ currentStep }: { currentStep: number }) {
  const { t } = useTranslation()
  const steps = [
    t('compare.stepParseOld'),
    t('compare.stepParseNew'),
    t('compare.stepDiff'),
    t('compare.stepRisk'),
    t('compare.stepTraps'),
    t('compare.stepReport'),
  ]

  return (
    <div className="analysis-progress compare-progress">
      <div className="progress-spinner" />
      <h3>{t('compare.analyzing')}</h3>
      <div className="progress-steps">
        {steps.map((step, i) => (
          <div
            key={i}
            className={`progress-step ${i < currentStep ? 'done' : i === currentStep ? 'active' : ''}`}
          >
            <span className="step-number">{i < currentStep ? '✓' : i + 1}</span>
            <span className="step-name">{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Compare() {
  const { t } = useTranslation()
  const { isLoggedIn, user, setShowLogin } = useAuth()
  const { showToast } = useToast()
  const [oldFile, setOldFile] = useState<File | null>(null)
  const [newFile, setNewFile] = useState<File | null>(null)
  const [isComparing, setIsComparing] = useState(false)
  const [compareStep, setCompareStep] = useState(0)
  const [report, setReport] = useState<CompareReport | null>(null)
  const [showSubModal, setShowSubModal] = useState(false)
  const [subModalReason, setSubModalReason] = useState('')
  const oldFileRef = useRef<HTMLInputElement>(null)
  const newFileRef = useRef<HTMLInputElement>(null)
  const stepIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current)
      }
    }
  }, [])

  const checkUsage = async (): Promise<boolean> => {
    if (!isLoggedIn || !user) return false
    try {
      const res = await api.get(`/api/contracts/usage/${user.id}`)
      const data = res.data
      if (data.compare.remaining <= 0) {
        setSubModalReason(t('subscription.reasonCompare', { limit: data.compare.limit }))
        setShowSubModal(true)
        return false
      }
      return true
    } catch {
      return true
    }
  }

  const handleFileSelect = (which: 'old' | 'new') => (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isLoggedIn) {
      setShowLogin(true)
      return
    }
    const file = e.target.files?.[0]
    if (file) {
      if (which === 'old') setOldFile(file)
      else setNewFile(file)
    }
  }

  const handleClick = (e: React.MouseEvent, which: 'old' | 'new') => {
    e.stopPropagation()
    if (!isLoggedIn) {
      setShowLogin(true)
      return
    }
    if (which === 'old') oldFileRef.current?.click()
    else newFileRef.current?.click()
  }

  const handleCompare = async () => {
    if (!oldFile && !newFile) {
      showToast(t('compare.selectBothFiles'), 'warning')
      return
    }
    if (!oldFile) {
      showToast(t('compare.missingOldFile'), 'warning')
      return
    }
    if (!newFile) {
      showToast(t('compare.missingNewFile'), 'warning')
      return
    }

    const ok = await checkUsage()
    if (!ok) return

    setReport(null)
    setIsComparing(true)
    setCompareStep(0)

    // Simulate progress steps to ease user anxiety while the sync pipeline runs.
    stepIntervalRef.current = setInterval(() => {
      setCompareStep((prev) => {
        if (prev >= COMPARE_STEPS - 1) {
          if (stepIntervalRef.current) clearInterval(stepIntervalRef.current)
          return prev
        }
        return prev + 1
      })
    }, 10000)

    try {
      const formData = new FormData()
      formData.append('old_file', oldFile)
      formData.append('new_file', newFile)
      formData.append('user_id', String(user?.id || 0))

      const res = await api.post('/api/contracts/compare', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current)
        stepIntervalRef.current = null
      }

      const result = res.data.report
      if (result && !result.error) {
        setCompareStep(COMPARE_STEPS - 1)
        setTimeout(() => {
          setReport(result)
          setIsComparing(false)
        }, 600)
      } else {
        setCompareStep(0)
        setIsComparing(false)
        showToast(result?.error || t('compare.comparisonFailed'), 'error')
      }
    } catch (err: any) {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current)
        stepIntervalRef.current = null
      }
      setCompareStep(0)
      setIsComparing(false)
      showToast(err.response?.data?.detail || t('compare.comparisonFailed'), 'error')
    }
  }

  const handleReset = () => {
    setOldFile(null)
    setNewFile(null)
    setReport(null)
  }

  const handleRemoveFile = (e: React.MouseEvent, which: 'old' | 'new') => {
    e.stopPropagation()
    if (which === 'old') {
      setOldFile(null)
      if (oldFileRef.current) oldFileRef.current.value = ''
    } else {
      setNewFile(null)
      if (newFileRef.current) newFileRef.current.value = ''
    }
  }

  if (report) {
    return <CompareResult report={report} onReset={handleReset} />
  }

  if (isComparing) {
    return (
      <div className="page compare-page">
        <CompareProgress currentStep={compareStep} />
      </div>
    )
  }

  return (
    <div className="page compare-page">
      {!isLoggedIn ? (
        <div className="hero-wrapper">
          <div className="hero-section">
            <span className="hero-eyebrow">{t('compare.heroEyebrow')}</span>
            <h1 className="hero-title">
              {t('compare.heroTitlePart1')}<br />
              {t('compare.heroTitlePart2')} <em className="serif-italic">{t('compare.heroTitleItalic')}</em>
            </h1>
            <p className="hero-subtitle">
              {t('compare.heroSubtitle')}
            </p>
          </div>

          <div className="compare-uploads">
            <div
              className={`upload-zone ${oldFile ? 'has-file' : ''}`}
              onClick={(e) => handleClick(e, 'old')}
            >
              <input
                ref={oldFileRef}
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                style={{ display: 'none' }}
                onChange={handleFileSelect('old')}
              />
              <div className="upload-icon-wrap">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <h3>{t('compare.oldVersion')}</h3>
              {oldFile ? (
                <div className="file-selected">
                  <p className="file-name">{oldFile.name}</p>
                  <button
                    className="file-remove"
                    onClick={(e) => handleRemoveFile(e, 'old')}
                    title={t('common.delete')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              ) : (
                <p className="text-muted">{t('compare.clickToSelect')}</p>
              )}
            </div>

            <div
              className={`upload-zone ${newFile ? 'has-file' : ''}`}
              onClick={(e) => handleClick(e, 'new')}
            >
              <input
                ref={newFileRef}
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                style={{ display: 'none' }}
                onChange={handleFileSelect('new')}
              />
              <div className="upload-icon-wrap">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <h3>{t('compare.newVersion')}</h3>
              {newFile ? (
                <div className="file-selected">
                  <p className="file-name">{newFile.name}</p>
                  <button
                    className="file-remove"
                    onClick={(e) => handleRemoveFile(e, 'new')}
                    title={t('common.delete')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              ) : (
                <p className="text-muted">{t('compare.clickToSelect')}</p>
              )}
            </div>
          </div>

          <div className="compare-actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={handleCompare}
              disabled={isComparing}
            >
              {isComparing ? t('common.loading') : t('compare.compareButton')}
            </button>
            {(oldFile || newFile) && (
              <button className="btn btn-ghost" onClick={handleReset}>
                {t('common.cancel')}
              </button>
            )}
          </div>

        </div>
      ) : (
        <>
          {isLoggedIn && (
            <UserGreeting variant="compare" />
          )}

          <div className="compare-uploads">
            <div
              className={`upload-zone ${oldFile ? 'has-file' : ''}`}
              onClick={(e) => handleClick(e, 'old')}
            >
              <input
                ref={oldFileRef}
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                style={{ display: 'none' }}
                onChange={handleFileSelect('old')}
              />
              <div className="upload-icon-wrap">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <h3>{t('compare.oldVersion')}</h3>
              {oldFile ? (
                <div className="file-selected">
                  <p className="file-name">{oldFile.name}</p>
                  <button
                    className="file-remove"
                    onClick={(e) => handleRemoveFile(e, 'old')}
                    title={t('common.delete')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              ) : (
                <p className="text-muted">{t('compare.clickToSelect')}</p>
              )}
            </div>

            <div
              className={`upload-zone ${newFile ? 'has-file' : ''}`}
              onClick={(e) => handleClick(e, 'new')}
            >
              <input
                ref={newFileRef}
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                style={{ display: 'none' }}
                onChange={handleFileSelect('new')}
              />
              <div className="upload-icon-wrap">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <h3>{t('compare.newVersion')}</h3>
              {newFile ? (
                <div className="file-selected">
                  <p className="file-name">{newFile.name}</p>
                  <button
                    className="file-remove"
                    onClick={(e) => handleRemoveFile(e, 'new')}
                    title={t('common.delete')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              ) : (
                <p className="text-muted">{t('compare.clickToSelect')}</p>
              )}
            </div>
          </div>

          <div className="compare-actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={handleCompare}
              disabled={isComparing}
            >
              {isComparing ? t('common.loading') : t('compare.compareButton')}
            </button>
            {(oldFile || newFile) && (
              <button className="btn btn-ghost" onClick={handleReset}>
                {t('common.cancel')}
              </button>
            )}
          </div>

        </>
      )}

      {/* SEO content (public users only) */}
      {!isLoggedIn && <SEOContent variant="compare" />}

      {showSubModal && (
        <SubscriptionModal
          reason={subModalReason}
          onClose={() => setShowSubModal(false)}
        />
      )}
    </div>
  )
}

