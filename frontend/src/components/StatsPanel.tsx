import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'

interface UserStats {
  totalAnalyzes: number
  thisWeekChange: number
  highRiskFound: number
  averageRiskScore: number
  lastAnalyzeTime: string
  riskTypeDistribution: { category: string; count: number; percentage: number }[]
}

const SLICE_COLORS = ['#f97316', '#10b981', '#fbbf24', '#6366f1', '#ef4444', '#0ea5e9']

function PieChart({ slices }: { slices: { percentage: number; color: string }[] }) {
  const radius = 60
  const cx = 70
  const cy = 70
  let cumulative = 0
  const total = slices.reduce((s, x) => s + x.percentage, 0)
  if (total === 0) {
    return (
      <svg viewBox="0 0 140 140" className="pie-chart">
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke="var(--border-color)" strokeWidth="14" />
      </svg>
    )
  }
  const arcs = slices
    .filter((s) => s.percentage > 0)
    .map((s, i) => {
      const startAngle = (cumulative / 100) * 2 * Math.PI - Math.PI / 2
      cumulative += s.percentage
      const endAngle = (cumulative / 100) * 2 * Math.PI - Math.PI / 2
      const x1 = cx + radius * Math.cos(startAngle)
      const y1 = cy + radius * Math.sin(startAngle)
      const x2 = cx + radius * Math.cos(endAngle)
      const y2 = cy + radius * Math.sin(endAngle)
      const largeArc = s.percentage > 50 ? 1 : 0
      const path = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`
      return <path key={i} d={path} fill={s.color} />
    })
  return (
    <svg viewBox="0 0 140 140" className="pie-chart">
      {arcs}
      <circle cx={cx} cy={cy} r={32} fill="var(--bg-card)" />
    </svg>
  )
}

export default function StatsPanel() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user?.id) return
    setLoading(true)
    api
      .get('/api/stats/user', { params: { user_id: user.id } })
      .then((res) => setStats(res.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [user?.id])

  if (loading || !stats) {
    return (
      <div className="stats-panel stats-panel-loading">
        <div className="progress-spinner" />
      </div>
    )
  }

  const distribution = stats.riskTypeDistribution.map((d, i) => ({
    ...d,
    color: SLICE_COLORS[i % SLICE_COLORS.length],
  }))

  return (
    <section className="stats-panel">
      <div className="stats-panel-header">
        <span className="stats-panel-eyebrow">{t('stats.eyebrow')}</span>
        <h2 className="stats-panel-title">
          {t('stats.titlePrefix')} <em className="serif-italic">{t('stats.titleItalic')}</em>
        </h2>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">{t('stats.totalAnalyzes')}</span>
          <span className="stat-value">{stats.totalAnalyzes}</span>
          {stats.thisWeekChange > 0 && (
            <span className="stat-trend">+{stats.thisWeekChange} {t('stats.thisWeek')}</span>
          )}
        </div>
        <div className="stat-card">
          <span className="stat-label">{t('stats.highRiskFound')}</span>
          <span className="stat-value">{stats.highRiskFound}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">{t('stats.averageRiskScore')}</span>
          <span className="stat-value">{stats.averageRiskScore || '—'}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">{t('stats.lastAnalyze')}</span>
          <span className="stat-value-text">{stats.lastAnalyzeTime}</span>
        </div>
      </div>

      <div className="stats-distribution">
        <div className="stats-distribution-chart">
          <PieChart slices={distribution.map((d) => ({ percentage: d.percentage, color: d.color }))} />
        </div>
        <div className="stats-distribution-legend">
          <h4>{t('stats.distributionTitle')}</h4>
          {distribution.length === 0 ? (
            <p className="text-muted">{t('stats.noData')}</p>
          ) : (
            <ul>
              {distribution.map((d, i) => (
                <li key={i}>
                  <span className="legend-dot" style={{ background: d.color }} />
                  <span className="legend-label">{d.category}</span>
                  <span className="legend-percent">{d.percentage}%</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}
