import { useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'

interface AnalysisReport {
  contractType: string
  jurisdiction: string
  overallScore: number
  summary: string
  riskBreakdown: { high: number; medium: number; low: number }
  riskyClauses: Array<{
    id: string
    severity: string
    clauseTitle: string
    originalText: string
    plainExplanation: string
    legalBasis: string
    solution: string
    negotiationScript: { yourOpening: string; theirRebuttal: string; yourResponse: string }
  }>
  missingClauses: Array<{
    id: string
    severity: string
    title: string
    description: string
    suggestedText: string
  }>
  keyTerms: Array<{ term: string; plainMeaning: string }>
  keyDates: Array<{ description: string; originalText: string; date: string; daysRemaining?: number }>
}

export default function Home() {
  const { t } = useTranslation()
  const { isLoggedIn, user } = useAuth()
  const [isDragging, setIsDragging] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState({ step: 0, stepName: '' })
  const [report, setReport] = useState<AnalysisReport | null>(null)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFile(files[0])
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const handleFile = async (file: File) => {
    if (!isLoggedIn) {
      setError('Please login first')
      return
    }

    setError('')
    setReport(null)
    setIsAnalyzing(true)
    setProgress({ step: 1, stepName: t('home.step1') })

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', String(user?.id || 1))

      const res = await api.post('/api/contracts/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      const { contract_record_id } = res.data

      // Poll for result
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.get(`/api/contracts/analyze/${contract_record_id}/status`)
          if (statusRes.data.report) {
            clearInterval(pollInterval)
            setReport(statusRes.data.report)
            setIsAnalyzing(false)
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 3000)

      // Timeout after 2 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        if (!report) {
          setIsAnalyzing(false)
          setError('Analysis timed out. Please try again.')
        }
      }, 120000)

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed')
      setIsAnalyzing(false)
    }
  }

  if (report) {
    return <AnalysisResult report={report} onReset={() => setReport(null)} />
  }

  return (
    <div className="page home-page">
      {isAnalyzing ? (
        <AnalysisProgress progress={progress} />
      ) : (
        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          <div className="upload-icon">📄 📁 📎</div>
          <h2>{t('home.uploadTitle')}</h2>
          <p>{t('home.uploadSubtitle')}</p>
          <p className="text-muted">{t('home.maxSize')}</p>
          <div className="divider">{t('common.or')}</div>
          <button className="btn btn-secondary" onClick={(e) => { e.stopPropagation(); }}>
            {t('home.pasteText')}
          </button>
          <p className="privacy-note">{t('home.privacyNote')}</p>
          {error && <p className="text-error">{error}</p>}
        </div>
      )}
    </div>
  )
}

function AnalysisProgress({ progress }: { progress: { step: number; stepName: string } }) {
  const { t } = useTranslation()
  const steps = [
    t('home.step1'),
    t('home.step2'),
    t('home.step3'),
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

function AnalysisResult({ report, onReset }: { report: AnalysisReport; onReset: () => void }) {
  const { t } = useTranslation()
  const [expandedClause, setExpandedClause] = useState<string | null>(null)

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#22c55e'
    if (score >= 40) return '#f97316'
    return '#ef4444'
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return '#ef4444'
      case 'medium': return '#f97316'
      case 'low': return '#22c55e'
      default: return '#6b7280'
    }
  }

  return (
    <div className="page report-page">
      <div className="report-header">
        <button className="btn btn-ghost" onClick={onReset}>← {t('common.back')}</button>
        <div className="report-score" style={{ color: getScoreColor(report.overallScore) }}>
          <span className="score-value">{report.overallScore}</span>
          <span className="score-label">{t('home.overallScore')}</span>
        </div>
      </div>

      <div className="report-card">
        <h3>{t('home.reportTitle')}</h3>
        <p className="report-summary">{report.summary}</p>

        <div className="risk-breakdown">
          <div className="risk-item high">
            <span className="risk-count">{report.riskBreakdown.high}</span>
            <span className="risk-label">{t('home.riskHigh')}</span>
          </div>
          <div className="risk-item medium">
            <span className="risk-count">{report.riskBreakdown.medium}</span>
            <span className="risk-label">{t('home.riskMedium')}</span>
          </div>
          <div className="risk-item low">
            <span className="risk-count">{report.riskBreakdown.low}</span>
            <span className="risk-label">{t('home.riskLow')}</span>
          </div>
        </div>
      </div>

      {report.riskyClauses.length > 0 && (
        <div className="report-section">
          <h4>Risky Clauses</h4>
          {report.riskyClauses.map(clause => (
            <div key={clause.id} className="clause-card">
              <div
                className="clause-header"
                onClick={() => setExpandedClause(expandedClause === clause.id ? null : clause.id)}
              >
                <span className="clause-severity" style={{ background: getSeverityColor(clause.severity) }}>
                  {clause.severity}
                </span>
                <span className="clause-title">{clause.clauseTitle}</span>
                <span className="clause-toggle">{expandedClause === clause.id ? '−' : '+'}</span>
              </div>
              {expandedClause === clause.id && (
                <div className="clause-body">
                  <p><strong>Original:</strong> {clause.originalText}</p>
                  <p><strong>Explanation:</strong> {clause.plainExplanation}</p>
                  <p><strong>Legal Basis:</strong> {clause.legalBasis}</p>
                  <p><strong>Solution:</strong> {clause.solution}</p>
                  {clause.negotiationScript && (
                    <div className="negotiation-script">
                      <p><strong>You:</strong> {clause.negotiationScript.yourOpening}</p>
                      <p><strong>Them:</strong> {clause.negotiationScript.theirRebuttal}</p>
                      <p><strong>You:</strong> {clause.negotiationScript.yourResponse}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {report.missingClauses.length > 0 && (
        <div className="report-section">
          <h4>{t('home.missingClauses')}</h4>
          {report.missingClauses.map(clause => (
            <div key={clause.id} className="clause-card">
              <div className="clause-header">
                <span className="clause-severity" style={{ background: getSeverityColor(clause.severity) }}>
                  {clause.severity}
                </span>
                <span className="clause-title">{clause.title}</span>
              </div>
              <div className="clause-body">
                <p>{clause.description}</p>
                <p><strong>Suggested:</strong> {clause.suggestedText}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {report.keyTerms.length > 0 && (
        <div className="report-section">
          <h4>{t('home.keyTerms')}</h4>
          <div className="terms-grid">
            {report.keyTerms.map((term, i) => (
              <div key={i} className="term-card">
                <span className="term-name">{term.term}</span>
                <span className="term-meaning">{term.plainMeaning}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.keyDates.length > 0 && (
        <div className="report-section">
          <h4>{t('home.keyDates')}</h4>
          <div className="dates-list">
            {report.keyDates.map((date, i) => (
              <div key={i} className="date-item">
                <span className="date-value">{date.date}</span>
                <span className="date-desc">{date.description}</span>
                {date.daysRemaining !== undefined && (
                  <span className="date-remaining">{date.daysRemaining} days remaining</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="report-actions">
        <button className="btn btn-primary">{t('home.downloadPDF')}</button>
        <button className="btn btn-secondary">{t('home.downloadWord')}</button>
      </div>
    </div>
  )
}
