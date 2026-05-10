import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'

interface Contract {
  id: number
  file_name: string
  contract_type: string
  jurisdiction: string
  overall_score: number
  created_at: string
}

export default function Contracts() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const limit = 10

  useEffect(() => {
    if (!user) return
    loadContracts()
  }, [user, page])

  const loadContracts = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/api/contracts/my?user_id=${user?.id}&skip=${(page - 1) * limit}&limit=${limit}`)
      setContracts(res.data.contracts)
      setTotal(res.data.total)
    } catch (err) {
      console.error('Failed to load contracts', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm(t('contracts.confirmDelete'))) return
    try {
      await api.delete(`/api/contracts/${id}?user_id=${user?.id}`)
      loadContracts()
    } catch (err) {
      console.error('Failed to delete contract', err)
    }
  }

  const filtered = contracts.filter(c =>
    c.file_name.toLowerCase().includes(search.toLowerCase())
  )

  const totalPages = Math.ceil(total / limit)

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#22c55e'
    if (score >= 40) return '#f97316'
    return '#ef4444'
  }

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
              <div key={contract.id} className="contract-card">
                <div className="contract-info">
                  <h4 className="contract-name">{contract.file_name}</h4>
                  <div className="contract-meta">
                    <span>{contract.contract_type || 'Unknown'}</span>
                    <span>{contract.jurisdiction || 'Unknown'}</span>
                    <span
                      className="contract-score"
                      style={{ color: getScoreColor(contract.overall_score || 50) }}
                    >
                      {contract.overall_score || 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="contract-actions">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleDelete(contract.id)}
                  >
                    {t('common.delete')}
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
