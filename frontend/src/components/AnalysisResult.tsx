import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { api } from '../lib/api'

export interface AnalysisReport {
  contractType?: string
  jurisdiction?: string
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
  keyDates: Array<{ date: string; milestone?: string; daysRemaining?: number | null }>
}

interface Props {
  report: AnalysisReport
  contractId?: number
  fileName?: string
  onBack: () => void
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  pending?: boolean
}

const getSeverityClass = (severity: string) => {
  switch (severity) {
    case 'high': return 'sev-high'
    case 'medium': return 'sev-medium'
    case 'low': return 'sev-low'
    default: return 'sev-low'
  }
}

// Sort key for severity tiers — high comes first, low last. Used to render
// risky clauses in risk-descending order even for reports that were saved
// before backend-side sorting was added.
const SEVERITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 }
const bySeverity = (a: { severity: string }, b: { severity: string }) =>
  (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99)

const truncate = (text: string, n: number) =>
  text && text.length > n ? text.slice(0, n) + '…' : (text || '')

// Force "1. foo 2. bar 3. baz" onto separate lines. The LLM tends to inline
// numbered lists into a single paragraph; injecting newlines before each
// numbered marker makes those paragraphs scannable. Pattern matches
//   "1." / "1)" / "1、" / "①" etc. that follow whitespace or punctuation.
const ENUMERATED_BREAK_RE = /(?<!^)(?<=[\s.。;；!！?？)）"”\]])(?=(?:\(?\d{1,2}[.、)）]|[①-⑳])\s*\S)/gu
const formatNumberedContent = (text: string): string => {
  if (!text) return ''
  // If the writer already added line breaks, trust them.
  if (text.includes('\n')) return text
  return text.replace(ENUMERATED_BREAK_RE, '\n')
}

const formatRemainingTime = (days: number | null | undefined, t: (k: string, o?: any) => string): string | null => {
  if (typeof days !== 'number') return null
  if (days < 0) return t('home.daysOverdue', { count: Math.abs(days) })
  if (days === 0) return t('home.daysToday')
  return t('home.daysRemaining', { count: days })
}

export default function AnalysisResult({ report, contractId, fileName, onBack }: Props) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { showToast } = useToast()
  const [expandedClause, setExpandedClause] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<string>('overview')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [remainingRounds, setRemainingRounds] = useState<number>(10)
  const [downloading, setDownloading] = useState<'pdf' | 'docx' | null>(null)
  const chatScrollRef = useRef<HTMLDivElement>(null)

  const isPaid = user?.plan && user.plan !== 'free'

  // ---------------- TOC scroll-spy ----------------
  // IntersectionObserver was racy here: tall sections like "risky" would always win
  // because they stayed partially visible. We compare each section's top against an
  // "active line" near the top of the viewport on every scroll instead.
  useEffect(() => {
    const sectionIds = ['overview', 'risky', 'missing', 'dates', 'terms', 'chat']

    let frame = 0
    const update = () => {
      frame = 0
      // The fixed topbar sits at top=12 + ~52px tall; treat the active line ~140px down.
      const activeLine = 140
      let current = sectionIds[0]
      for (const id of sectionIds) {
        const el = document.getElementById(id)
        if (!el) continue
        const top = el.getBoundingClientRect().top
        if (top - activeLine <= 0) {
          current = id
        } else {
          break
        }
      }
      // Snap to the last section once the user reaches the bottom of the page.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        current = sectionIds[sectionIds.length - 1]
      }
      setActiveSection(current)
    }

    const onScroll = () => {
      if (frame) return
      frame = window.requestAnimationFrame(update)
    }

    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [])

  const scrollTo = (id: string) => {
    const el = document.getElementById(id)
    if (el) {
      const top = el.getBoundingClientRect().top + window.scrollY - 96
      window.scrollTo({ top, behavior: 'smooth' })
    }
  }

  // ---------------- Follow-up chat ----------------
  // Hydrate the chat panel from prior rounds whenever a new contract is opened
  // (re-entry from "My Contracts" hits this path; a fresh analysis won't have
  // any history so the call just returns an empty list).
  useEffect(() => {
    if (!contractId) {
      setMessages([])
      setRemainingRounds(10)
      return
    }
    const token = localStorage.getItem('spotclause-token') || ''
    if (!token) return
    let cancelled = false
    api
      .get(`/api/follow-up/messages/${contractId}`, { params: { token } })
      .then((res) => {
        if (cancelled) return
        const history = (res.data.messages || []).map((m: { role: string; content: string }) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
        }))
        setMessages(history)
        if (typeof res.data.remaining_rounds === 'number') {
          setRemainingRounds(res.data.remaining_rounds)
        }
      })
      .catch(() => {
        // Silent — leaving the panel empty is a fine fallback for a 401/404.
      })
    return () => {
      cancelled = true
    }
  }, [contractId])

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [messages, chatLoading])

  const sendChat = async () => {
    const q = chatInput.trim()
    if (!q || chatLoading) return
    if (!isPaid) {
      showToast(t('home.followUpDisabled'), 'warning')
      return
    }
    if (!contractId) {
      showToast(t('home.chatNoContract'), 'warning')
      return
    }
    setChatInput('')
    setMessages((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', pending: true }])
    setChatLoading(true)
    try {
      const token = localStorage.getItem('spotclause-token') || ''
      const res = await api.post(
        `/api/follow-up/chat/${contractId}`,
        null,
        { params: { question: q, token } }
      )
      setMessages((m) => {
        const next = [...m]
        next[next.length - 1] = { role: 'assistant', content: res.data.response }
        return next
      })
      if (typeof res.data.remaining_rounds === 'number') {
        setRemainingRounds(res.data.remaining_rounds)
      }
    } catch (err: any) {
      setMessages((m) => {
        const next = [...m]
        next[next.length - 1] = {
          role: 'assistant',
          content: err.response?.data?.detail || t('home.chatError'),
        }
        return next
      })
    } finally {
      setChatLoading(false)
    }
  }

  // ---------------- Download (PDF / DOCX) ----------------
  // We deliberately go through axios so the response error path (auth, 404,
  // report-not-yet-ready) surfaces as a toast instead of a broken file. The
  // browser-side download dance is the canonical blob → object-URL pattern.
  const downloadReport = async (format: 'pdf' | 'docx') => {
    if (!contractId) {
      showToast(t('home.exportNoContract'), 'warning')
      return
    }
    if (downloading) return
    setDownloading(format)
    try {
      const res = await api.get(`/api/contracts/${contractId}/export`, {
        params: { format, user_id: user?.id ?? 0 },
        responseType: 'blob',
      })
      const blob = res.data as Blob
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url

      // Server already sets Content-Disposition with the sanitised filename,
      // but EventSource downloads via blob lose that — derive a name on the
      // client too so it doesn't fall back to a random UUID.
      const baseName = (fileName || 'contract').replace(/\.[^.]+$/, '') || 'contract'
      a.download = `${baseName}-report.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err: any) {
      let msg = t('home.downloadFailed')
      // axios + responseType:blob means error.response.data is a Blob with the
      // JSON error body inside. Read it back so the user sees the real reason.
      const data = err?.response?.data
      if (data instanceof Blob) {
        try {
          const text = await data.text()
          const parsed = JSON.parse(text)
          if (parsed?.detail) msg = parsed.detail
        } catch {
          /* fall through to default msg */
        }
      } else if (typeof data === 'string') {
        msg = data
      } else if (data?.detail) {
        msg = data.detail
      }
      showToast(msg, 'error')
    } finally {
      setDownloading(null)
    }
  }

  // ---------------- TOC items ----------------
  const tocItems = [
    { id: 'overview', label: t('home.tocOverview') },
    { id: 'risky', label: t('home.tocRisky'), count: report.riskyClauses?.length },
    { id: 'missing', label: t('home.tocMissing'), count: report.missingClauses?.length },
    { id: 'dates', label: t('home.tocDates'), count: report.keyDates?.length },
    { id: 'terms', label: t('home.tocTerms'), count: report.keyTerms?.length },
    { id: 'chat', label: t('home.tocChat') },
  ]

  return (
    <div className="page report-page">
      {/* Floating top action bar */}
      <div className="report-topbar">
        <div className="report-topbar-inner">
          <button className="topbar-btn" onClick={onBack} aria-label={t('common.back')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5" />
              <path d="M12 19l-7-7 7-7" />
            </svg>
            <span>{t('common.back')}</span>
          </button>
          {fileName && <div className="topbar-filename" title={fileName}>{fileName}</div>}
          <div className="topbar-actions">
            <button
              className="topbar-btn"
              onClick={() => downloadReport('pdf')}
              disabled={downloading !== null || !contractId}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <span>{downloading === 'pdf' ? t('home.exporting') : t('home.downloadPDF')}</span>
            </button>
            <button
              className="topbar-btn"
              onClick={() => downloadReport('docx')}
              disabled={downloading !== null || !contractId}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>{downloading === 'docx' ? t('home.exporting') : t('home.downloadWord')}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="report-layout">
        {/* Main content */}
        <div className="report-main">
          {/* OVERVIEW */}
          <section id="overview" className="report-card overview-card">
            <div className="overview-head">
              <div className="overview-tags">
                {report.contractType && (
                  <span className="tag tag-type">{t(`contractTypes.${report.contractType}`, { defaultValue: report.contractType })}</span>
                )}
                {report.jurisdiction && (
                  <span className="tag tag-jurisdiction">{report.jurisdiction}</span>
                )}
              </div>
            </div>
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
          </section>

          {/* RISKY CLAUSES */}
          <section id="risky" className="report-section">
            <h4 className="section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              {t('home.riskyClauses')}
            </h4>
            {(!report.riskyClauses || report.riskyClauses.length === 0) ? (
              <div className="empty-section">{t('home.noRiskyClauses')}</div>
            ) : [...report.riskyClauses].sort(bySeverity).map((clause) => {
              const isOpen = expandedClause === clause.id
              // Collapsed header reads as a one-sentence risk description; we prefer
              // plainExplanation (LLM-written), fall back to legalBasis, then the
              // raw clause title if neither risk-summary field is populated.
              const headlineSource = clause.plainExplanation || clause.legalBasis || clause.clauseTitle || ''
              const headline = truncate(headlineSource.replace(/\s+/g, ' ').trim(), 90)
              return (
                <article key={clause.id} className={`clause-card ${getSeverityClass(clause.severity)} ${isOpen ? 'expanded' : ''}`}>
                  <button
                    className="clause-header"
                    onClick={() => setExpandedClause(isOpen ? null : clause.id)}
                  >
                    <span className={`sev-badge ${getSeverityClass(clause.severity)}`}>
                      {t(`severity.${clause.severity}`, { defaultValue: clause.severity })}
                    </span>
                    <span className="clause-title">{headline}</span>
                    <span className="clause-toggle" aria-hidden>
                      {isOpen ? '−' : '+'}
                    </span>
                  </button>
                  {!isOpen && clause.originalText && (
                    <div className="clause-preview">
                      <span className="preview-text clamp-2">{clause.originalText}</span>
                    </div>
                  )}
                  {isOpen && (
                    <div className="clause-body">
                      {clause.originalText && (
                        <div className="clause-block">
                          <div className="block-label">{t('home.labelOriginal')}</div>
                          <div className="block-content original">{clause.originalText}</div>
                        </div>
                      )}
                      {clause.legalBasis && (
                        <div className="clause-block">
                          <div className="block-label">{t('home.labelRiskReason')}</div>
                          <div className="block-content">{formatNumberedContent(clause.legalBasis)}</div>
                        </div>
                      )}
                      {clause.plainExplanation && (
                        <div className="clause-block">
                          <div className="block-label">{t('home.labelExplanation')}</div>
                          <div className="block-content">{formatNumberedContent(clause.plainExplanation)}</div>
                        </div>
                      )}
                      {clause.solution && (
                        <div className="clause-block">
                          <div className="block-label">{t('home.labelSolution')}</div>
                          <div className="block-content">{formatNumberedContent(clause.solution)}</div>
                        </div>
                      )}
                      {clause.negotiationScript && (clause.negotiationScript.yourOpening || clause.negotiationScript.theirRebuttal || clause.negotiationScript.yourResponse) && (
                        <div className="negotiation-block">
                          <div className="negotiation-title">{t('home.negotiationTitle')}</div>
                          {clause.negotiationScript.yourOpening && (
                            <div className="negotiation-line">
                              <span className="negotiation-tag self">{t('home.labelYou')}</span>
                              <span>{clause.negotiationScript.yourOpening}</span>
                            </div>
                          )}
                          {clause.negotiationScript.theirRebuttal && (
                            <div className="negotiation-line">
                              <span className="negotiation-tag other">{t('home.labelThem')}</span>
                              <span>{clause.negotiationScript.theirRebuttal}</span>
                            </div>
                          )}
                          {clause.negotiationScript.yourResponse && (
                            <div className="negotiation-line">
                              <span className="negotiation-tag self">{t('home.labelYou')}</span>
                              <span>{clause.negotiationScript.yourResponse}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </article>
              )
            })}
          </section>

          {/* MISSING CLAUSES */}
          <section id="missing" className="report-section">
            <h4 className="section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
              {t('home.missingClauses')}
            </h4>
            {(!report.missingClauses || report.missingClauses.length === 0) ? (
              <div className="empty-section">{t('home.noMissingClauses')}</div>
            ) : (
              <div className="missing-list">
                {report.missingClauses.map((m) => (
                  <article key={m.id} className={`missing-card ${getSeverityClass(m.severity)}`}>
                    <header>
                      <span className={`sev-badge ${getSeverityClass(m.severity)}`}>
                        {t(`severity.${m.severity}`, { defaultValue: m.severity })}
                      </span>
                      <span className="missing-title">{m.title}</span>
                    </header>
                    <p className="missing-desc">{formatNumberedContent(m.description)}</p>
                    {m.suggestedText && (
                      <div className="missing-suggested">
                        <span className="block-label">{t('home.labelSuggested')}</span>
                        <p>{formatNumberedContent(m.suggestedText)}</p>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* KEY DATES */}
          <section id="dates" className="report-section">
            <h4 className="section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              {t('home.keyDates')}
            </h4>
            {(!report.keyDates || report.keyDates.length === 0) ? (
              <div className="empty-section">{t('home.noKeyDates')}</div>
            ) : (
              <div className="dates-list">
                {report.keyDates.map((date, i) => {
                  const remaining = formatRemainingTime(date.daysRemaining, t)
                  const milestone = date.milestone?.trim() || t('home.milestoneUnnamed')
                  return (
                    <div key={`${date.date}-${i}`} className="date-item">
                      <span className="date-value">{date.date}</span>
                      {remaining && (
                        <span className={`date-remaining ${typeof date.daysRemaining === 'number' && date.daysRemaining < 0 ? 'overdue' : ''}`}>
                          {remaining}
                        </span>
                      )}
                      <span className="date-desc">{milestone}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* KEY TERMS */}
          <section id="terms" className="report-section">
            <h4 className="section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
              {t('home.keyTerms')}
            </h4>
            {(!report.keyTerms || report.keyTerms.length === 0) ? (
              <div className="empty-section">{t('home.noKeyTerms')}</div>
            ) : (
              <div className="terms-grid">
                {report.keyTerms.map((term, i) => (
                  <div key={i} className="term-card">
                    <span className="term-name">{term.term}</span>
                    <span className="term-meaning">{term.plainMeaning}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* FOLLOW-UP CHAT */}
          <section id="chat" className="report-section chat-section">
            <h4 className="section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              {t('home.followUpTitle')}
              {isPaid && <span className="rounds-pill">{t('home.roundsLeft', { count: remainingRounds })}</span>}
            </h4>
            {!isPaid ? (
              <div className="chat-locked">
                <div className="chat-locked-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <div className="chat-locked-body">
                  <h5>{t('home.chatLockedTitle')}</h5>
                  <p>{t('home.chatLockedDesc')}</p>
                  <a href="/pricing" className="btn btn-primary btn-sm">{t('home.unlockChat')}</a>
                </div>
              </div>
            ) : (
              <div className="chat-panel">
                <div ref={chatScrollRef} className="chat-scroll">
                  {messages.length === 0 ? (
                    <div className="chat-empty">{t('home.chatHint')}</div>
                  ) : (
                    messages.map((m, i) => (
                      <div key={i} className={`chat-bubble ${m.role}`}>
                        {m.pending ? <span className="chat-dots"><span></span><span></span><span></span></span> : m.content}
                      </div>
                    ))
                  )}
                </div>
                <div className="chat-input-row">
                  <input
                    type="text"
                    className="input chat-input"
                    placeholder={t('home.askFollowUp')}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        sendChat()
                      }
                    }}
                    disabled={chatLoading || remainingRounds <= 0}
                  />
                  <button
                    className="btn btn-primary chat-send"
                    onClick={sendChat}
                    disabled={chatLoading || !chatInput.trim() || remainingRounds <= 0}
                  >
                    {chatLoading ? '…' : t('common.send')}
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* TOC sidebar */}
        <aside className="report-toc">
          <div className="toc-title">{t('home.tocTitle')}</div>
          <ul>
            {tocItems.map((item) => (
              <li
                key={item.id}
                className={activeSection === item.id ? 'active' : ''}
              >
                <button onClick={() => scrollTo(item.id)}>
                  <span className="toc-label">{item.label}</span>
                  {typeof item.count === 'number' && item.count > 0 && (
                    <span className="toc-count">{item.count}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  )
}
