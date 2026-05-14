import { useTranslation } from 'react-i18next'

export interface Change {
  id: string
  location: string
  changeType: 'modified' | 'added' | 'removed'
  riskChange: 'improved' | 'worsened' | 'unchanged' | 'new'
  oldText?: string
  newText?: string
  analysis: string
}

export interface HiddenTrap {
  location: string
  description: string
  oldWording: string
  newWording: string
}

export interface CompareReport {
  summary: string
  breakdown?: {
    changes: number
    improved: number
    worsened: number
    unchanged: number
    new: number
    traps: number
  }
  overallRiskChange: 'improved' | 'worsened' | 'mixed'
  changes: Change[]
  hiddenTraps: HiddenTrap[]
}

interface Props {
  report: CompareReport
  onReset: () => void
}

export default function CompareResult({ report, onReset }: Props) {
  const { t } = useTranslation()

  const getRiskColor = (change: string) => {
    switch (change) {
      case 'improved': return '#22c55e'
      case 'worsened': return '#ef4444'
      case 'new': return '#f97316'
      default: return '#6b7280'
    }
  }

  const getRiskLabel = (change: string) => {
    switch (change) {
      case 'improved': return t('compare.improved')
      case 'worsened': return t('compare.worsened')
      case 'unchanged': return t('compare.unchanged')
      case 'new': return t('compare.new')
      default: return change
    }
  }

  return (
    <div className="page compare-result-page">
      {/* Floating top bar — same glass style as analysis report, no downloads */}
      <div className="report-topbar">
        <div className="report-topbar-inner">
          <button className="topbar-btn" onClick={onReset} aria-label={t('common.back')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5" />
              <path d="M12 19l-7-7 7-7" />
            </svg>
            <span>{t('common.back')}</span>
          </button>
          <div className="topbar-filename">{t('compare.reportTitle')}</div>
          <div className="topbar-actions" />
        </div>
      </div>

      <div className="report-card">
        <h3>{t('compare.reportTitle')}</h3>
        <p className="report-summary">
          {report.breakdown
            ? t('compare.summary', report.breakdown)
            : report.summary}
        </p>
        <p className="overall-risk" style={{ color: getRiskColor(report.overallRiskChange) }}>
          {t('compare.overall')} {getRiskLabel(report.overallRiskChange)}
        </p>
      </div>

      {report.changes?.length > 0 && (
        <div className="report-section">
          <h4>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            {t('compare.changes')} ({report.changes.length})
          </h4>
          {report.changes.map(change => (
            <div key={change.id} className="change-card">
              <div className="change-header">
                <span className="change-location">{change.location}</span>
                <span className="change-badge" style={{ background: getRiskColor(change.riskChange) }}>
                  {getRiskLabel(change.riskChange)}
                </span>
              </div>
              <div className="change-body">
                {change.oldText && (
                  <div className="change-old">
                    <span className="change-label">{t('compare.labelOld')}</span>
                    <p>{change.oldText}</p>
                  </div>
                )}
                {change.newText && (
                  <div className="change-new">
                    <span className="change-label">{t('compare.labelNew')}</span>
                    <p>{change.newText}</p>
                  </div>
                )}
                <p className="change-analysis">{change.analysis}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {report.hiddenTraps?.length > 0 && (
        <div className="report-section">
          <h4>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            {t('compare.hiddenTraps')}
          </h4>
          {report.hiddenTraps.map((trap, i) => (
            <div key={i} className="trap-card">
              <h5>{trap.location}</h5>
              <p>{trap.description}</p>
              <div className="trap-comparison">
                <div><strong>{t('compare.labelWas')}</strong> {trap.oldWording}</div>
                <div><strong>{t('compare.labelNow')}</strong> {trap.newWording}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
