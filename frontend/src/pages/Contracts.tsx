import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { api } from '../lib/api'

interface Contract {
  id: number
  file_name: string
  record_type: string
  contract_type: string
  jurisdiction: string
  status: string | null
  created_at: string
}

interface TypeCounts {
  all: number
  analysis: number
  comparison: number
}

type FilterType = 'all' | 'analysis' | 'comparison'

const StatusBadge = ({ status }: { status: string | null }) => {
  if (!status) return null
  const cls = `contract-status status-${status}`
  const label = status === 'pending' ? 'Analyzing...' : status === 'failed' ? 'Failed' : ''
  return <span className={cls}>{label}</span>
}

export default function Contracts() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [counts, setCounts] = useState<TypeCounts>({ all: 0, analysis: 0, comparison: 0 })
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [loading, setLoading] = useState(true)

  const limit = 10

  useEffect(() => {
    if (!user) return
    loadContracts()
  }, [user, page, activeFilter])

  const loadContracts = async () => {
    setLoading(true)
    try {
      const typeParam = activeFilter === 'all' ? '' : activeFilter
      const res = await api.get(
        `/api/contracts/my?user_id=${user?.id}&record_type=${typeParam}&skip=${(page - 1) * limit}&limit=${limit}`
      )
      setContracts(res.data.contracts)
      setTotal(res.data.total)
      if (res.data.counts) {
        setCounts(res.data.counts)
      }
    } catch (err) {
      console.error('Failed to load contracts', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (!confirm(t('contracts.confirmDelete'))) return
    try {
      await api.delete(`/api/contracts/${id}?user_id=${user?.id}`)
      showToast(t('contracts.deleted'), 'success')
      loadContracts()
    } catch (err) {
      console.error('Failed to delete contract', err)
      showToast(t('common.error'), 'error')
    }
  }

  const openReport = (id: number) => {
    navigate(`/contracts/${id}`)
  }

  const filtered = contracts.filter(c =>
    c.file_name.toLowerCase().includes(search.toLowerCase())
  )

  const totalPages = Math.ceil(total / limit)

  const filterTabs: { key: FilterType; label: string; count: number }[] = [
    { key: 'all', label: t('contracts.filterAll'), count: counts.all },
    { key: 'analysis', label: t('contracts.tagReview'), count: counts.analysis },
    { key: 'comparison', label: t('contracts.tagCompare'), count: counts.comparison },
  ]

  return (
    <div className="page contracts-page">
      <h1>{t('contracts.title')}</h1>

      <div className="contracts-toolbar">
        <input
          type="text"
          className="input"
          placeholder={t('contracts.search')}
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="contract-filters">
        {filterTabs.map(tab => (
          <button
            key={tab.key}
            className={`filter-tab ${activeFilter === tab.key ? 'active' : ''}`}
            onClick={() => { setActiveFilter(tab.key); setPage(1) }}
          >
            {tab.label}
            <span className="filter-count">{tab.count}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-muted">{t('common.loading')}</p>
      ) : filtered.length === 0 ? (
        <div className="contracts-empty">
          <p className="text-muted">{t('contracts.noContracts')}</p>
        </div>
      ) : (
        <>
          <div className="contracts-list">
            {filtered.map(contract => (
              <div
                key={contract.id}
                className="contract-card clickable"
                onClick={() => openReport(contract.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') openReport(contract.id) }}
              >
                <div className="contract-info">
                  <h4 className="contract-name">{contract.file_name}</h4>
                  <div className="contract-meta">
                    <span className={`contract-tag tag-${contract.record_type}`}>
                      {contract.record_type === 'comparison'
                        ? t('contracts.tagCompare')
                        : t('contracts.tagReview')}
                    </span>
                    <span>{contract.contract_type || t('contracts.unknownType')}</span>
                    <span>{contract.jurisdiction || t('contracts.unknownJurisdiction')}</span>
                    <StatusBadge status={contract.status} />
                  </div>
                </div>
                <div className="contract-actions">
                  <button
                    className="btn-icon-delete"
                    onClick={(e) => handleDelete(e, contract.id)}
                    title={t('common.delete')}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="contracts-pagination">
              <button
                className="btn btn-ghost btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                {t('common.back')}
              </button>
              <span className="text-muted">
                {t('contracts.pageOf', { current: page, total: totalPages })}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                {t('common.next')}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
