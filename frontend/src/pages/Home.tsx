import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Helmet } from 'react-helmet-async'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { api } from '../lib/api'
import SEOContent from '../components/SEOContent'
import UserGreeting from '../components/UserGreeting'
import StatsPanel from '../components/StatsPanel'
import SubscriptionModal from '../components/SubscriptionModal'
import AnalysisResult, { type AnalysisReport } from '../components/AnalysisResult'

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

// Maps the backend's phase event names to the four-step UI progress index.
// Anything else (e.g. clause_progress while in "analyze") keeps the same step
// and just updates the label.
const PHASE_TO_STEP: Record<string, number> = {
  parse: 1,
  structure: 2,
  analyze: 3,
  assemble: 4,
}

export default function Home() {
  const { t } = useTranslation()
  const { isLoggedIn, user, setShowLogin } = useAuth()
  const { showToast } = useToast()
  const [isDragging, setIsDragging] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState({ step: 0, stepName: '' })
  const [report, setReport] = useState<AnalysisReport | null>(null)
  const [contractRecordId, setContractRecordId] = useState<number | null>(null)
  const [currentFileName, setCurrentFileName] = useState<string>('')
  const [showSubModal, setShowSubModal] = useState(false)
  const [subModalReason, setSubModalReason] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const sseRef = useRef<EventSource | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Clean up any open SSE or polling timer on unmount
  useEffect(() => {
    return () => {
      sseRef.current?.close()
      sseRef.current = null
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    }
  }, [])

  const checkUsage = async (): Promise<boolean> => {
    if (!isLoggedIn || !user) return false
    try {
      const res = await api.get(`/api/contracts/usage/${user.id}`)
      const data = res.data
      if (data.analyze.remaining <= 0) {
        setSubModalReason(t('subscription.reasonAnalyze', { limit: data.analyze.limit }))
        setShowSubModal(true)
        return false
      }
      return true
    } catch {
      return true
    }
  }

  // Clean up any open SSE on unmount — leaks would keep the backend stream
  // alive past the user navigating away.
  useEffect(() => {
    return () => {
      sseRef.current?.close()
      sseRef.current = null
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (isLoggedIn) setIsDragging(true)
  }, [isLoggedIn])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (!isLoggedIn) {
      setShowLogin(true)
      return
    }
    const ok = await checkUsage()
    if (!ok) return
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFile(files[0])
    }
  }, [isLoggedIn, setShowLogin, user])

  const lastClickTime = useRef(0)

  const handleClick = (e?: React.MouseEvent) => {
    e?.stopPropagation()
    const now = Date.now()
    if (now - lastClickTime.current < 500) return
    lastClickTime.current = now
    if (!isLoggedIn) {
      setShowLogin(true)
      return
    }
    fileInputRef.current?.click()
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const handleFile = async (file: File) => {
    if (!isLoggedIn) {
      setShowLogin(true)
      return
    }

    const ok = await checkUsage()
    if (!ok) return

    // Tear down any prior stream or polling timer from a previous run
    sseRef.current?.close()
    sseRef.current = null
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }

    setReport(null)
    setIsAnalyzing(true)
    setProgress({ step: 1, stepName: t('home.step1') })

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', String(user?.id || 0))

      const res = await api.post('/api/contracts/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      const { contract_record_id } = res.data
      setContractRecordId(contract_record_id)
      setCurrentFileName(file.name)

      // Open the SSE stream. Cache hits emit a single complete event; misses
      // emit phase + clause_progress events as the pipeline runs.
      const es = new EventSource(`${API_BASE}/api/contracts/analyze/${contract_record_id}/stream`)
      sseRef.current = es
      let finished = false

      const teardown = () => {
        finished = true
        es.close()
        if (sseRef.current === es) sseRef.current = null
      }

      es.onmessage = (e) => {
        if (!e.data) return
        let evt: any
        try {
          evt = JSON.parse(e.data)
        } catch {
          return
        }
        // DEBUG: log every SSE event to browser console
        // eslint-disable-next-line no-console
        console.log('[SSE]', evt.type, evt)
        switch (evt.type) {
          case 'phase': {
            const step = PHASE_TO_STEP[evt.name] ?? progress.step
            // For the analyze phase the backend sends `total` (clause count)
            // so we can render "Analyzing clause 0/N..." without the ugly 0/0
            // flash before the first clause_progress event arrives.
            const total = typeof evt.total === 'number' ? evt.total : 0
            setProgress({
              step,
              stepName: phaseLabel(evt.name, t, total),
            })
            break
          }
          case 'structure_done':
            setProgress({
              step: 3,
              stepName: t('home.step3', { current: 0, total: evt.clauseCount || 0 }),
            })
            break
          case 'clause_progress':
            setProgress({
              step: 3,
              stepName: t('home.step3', { current: evt.completed, total: evt.total }),
            })
            break
          case 'side_info_done':
            // side-info finishes alongside clause analysis; no step bump
            break
          case 'complete':
            if (pollTimerRef.current) {
              clearInterval(pollTimerRef.current)
              pollTimerRef.current = null
            }
            setReport(evt.report)
            setIsAnalyzing(false)
            teardown()
            break
          case 'error':
            if (pollTimerRef.current) {
              clearInterval(pollTimerRef.current)
              pollTimerRef.current = null
            }
            showToast(evt.message || t('home.analysisFailed'), 'error')
            setIsAnalyzing(false)
            teardown()
            break
          default:
            break
        }
      }

      // When the SSE drops (e.g. Render 100s timeout, proxy idle timeout),
      // fall back to polling the DB so the analysis can finish in the
      // background without the user seeing a fake failure toast.
      const startPolling = () => {
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current)
        }
        // Keep the current progress label instead of jumping to step 4 so the
        // user still sees the last known step (e.g. "Reviewing clause 3/5...")
        pollTimerRef.current = setInterval(async () => {
          try {
            const statusRes = await api.get(`/api/contracts/analyze/${contract_record_id}/status`)
            const data = statusRes.data
            if (data.report) {
              if (pollTimerRef.current) {
                clearInterval(pollTimerRef.current)
                pollTimerRef.current = null
              }
              setReport(data.report)
              setIsAnalyzing(false)
            }
            if (data.error) {
              if (pollTimerRef.current) {
                clearInterval(pollTimerRef.current)
                pollTimerRef.current = null
              }
              showToast(data.error || t('home.analysisFailed'), 'error')
              setIsAnalyzing(false)
            }
          } catch {
            // Polling errors are silent — we'll try again in 5s.
          }
        }, 5000)
      }

      es.onerror = () => {
        if (finished) return
        teardown()
        // Don't show an error — the backend is still crunching in the
        // background task. Switch to polling instead.
        startPolling()
      }

    } catch (err: any) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      showToast(err.response?.data?.detail || t('home.analysisFailed'), 'error')
      setIsAnalyzing(false)
      sseRef.current?.close()
      sseRef.current = null
    }
  }

  if (report) {
    return (
      <AnalysisResult
        report={report}
        contractId={contractRecordId ?? undefined}
        fileName={currentFileName}
        onBack={() => { setReport(null); setContractRecordId(null); setCurrentFileName('') }}
      />
    )
  }

  return (
    <>
      <Helmet>
        <title>SpotClause - AI Contract Reader | Free Contract Analysis Tool</title>
        <meta name="description" content="AI-powered contract reading for freelancers and small businesses. Spot unfair clauses, compare contract versions, and understand what you're signing before you sign." />
        <link rel="canonical" href="https://spotclause.app" />
        <meta property="og:title" content="SpotClause - AI Contract Reader" />
        <meta property="og:description" content="AI-powered contract reading for freelancers and small businesses. Spot key clauses before you sign." />
        <meta property="og:image" content="https://spotclause.app/og-review.jpg" />
        <meta property="og:url" content="https://spotclause.app" />
        <meta name="twitter:image" content="https://spotclause.app/og-review.jpg" />
      </Helmet>
      <div className="page home-page">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
        onClick={(e) => e.stopPropagation()}
      />
      {!isLoggedIn && !isAnalyzing ? (
        <div className="hero-wrapper">
          <div className="hero-section">
            <span className="hero-eyebrow">{t('home.heroEyebrow')}</span>
            <h1 className="hero-title">
              {t('home.heroTitlePart1')} <em className="serif-italic">{t('home.heroTitleItalic')}</em><br />
              {t('home.heroTitlePart2')}
            </h1>
            <p className="hero-subtitle">
              {t('home.heroSubtitle')}
            </p>
          </div>

          <div
            className={`upload-zone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
          >
            <div className="upload-icon-wrap">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <h2>{t('home.uploadTitle')}</h2>
            <p>{t('home.uploadSubtitle')}</p>
            <p className="text-muted">{t('home.maxSize')}</p>
            <p className="privacy-note">{t('home.privacyNote')}</p>
          </div>
        </div>
      ) : isAnalyzing ? (
        <AnalysisProgress progress={progress} />
      ) : (
        <div className="logged-home-wrap">
          <UserGreeting variant="review" />
          <div
            className={`upload-zone logged-upload ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
          >
            <div className="upload-icon-wrap">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <h2>{t('home.uploadTitle')}</h2>
            <p>{t('home.uploadSubtitle')}</p>
            <p className="text-muted">{t('home.maxSize')}</p>
            <p className="privacy-note">{t('home.privacyNote')}</p>
          </div>
          <StatsPanel />
        </div>
      )}

      {/* SEO content (public users only) */}
      {!isLoggedIn && !isAnalyzing && <SEOContent variant="review" />}

      {showSubModal && (
        <SubscriptionModal
          reason={subModalReason}
          onClose={() => setShowSubModal(false)}
        />
      )}
    </div>
    </>
  )
}

function phaseLabel(name: string, t: (k: string, opts?: any) => string, total = 0): string {
  switch (name) {
    case 'parse': return t('home.step1')
    case 'structure': return t('home.step2')
    case 'analyze': return t('home.step3', { current: 0, total })
    case 'assemble': return t('home.step4')
    default: return t('home.analyzing')
  }
}

function AnalysisProgress({ progress }: { progress: { step: number; stepName: string } }) {
  const { t } = useTranslation()
  const step3Ref = useRef(t('home.step3', { current: 0, total: 0 }))
  if (progress.step === 3 && progress.stepName) {
    step3Ref.current = progress.stepName
  }
  const steps = [
    t('home.step1'),
    t('home.step2'),
    step3Ref.current,
    t('home.step4'),
  ]

  return (
    <div className="analysis-progress">
      <div className="progress-spinner" />
      <h3>{t('home.analyzing')}</h3>
      <div className="progress-steps">
        {steps.map((step, i) => (
          <div key={i} className={`progress-step ${i + 1 < progress.step ? 'done' : i + 1 === progress.step ? 'active' : ''}`}>
            <span className="step-number">{i + 1 < progress.step ? '✓' : i + 1}</span>
            <span className="step-name">{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
