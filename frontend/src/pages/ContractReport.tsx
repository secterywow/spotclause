import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../lib/api'
import AnalysisResult, { type AnalysisReport } from '../components/AnalysisResult'
import CompareResult, { type CompareReport } from '../components/CompareResult'

export default function ContractReport() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<AnalysisReport | CompareReport | null>(null)
  const [recordType, setRecordType] = useState<string>('')
  const [fileName, setFileName] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const res = await api.get(`/api/contracts/analyze/${id}/status`)
        if (cancelled) return
        setRecordType(res.data.record_type || 'analysis')
        setFileName(res.data.file_name || '')
        if (res.data.report && !res.data.report.error) {
          setReport(res.data.report)
        } else if (res.data.report?.error) {
          setError(res.data.report.error)
        } else {
          setError(t('contracts.reportPending'))
        }
      } catch (err: any) {
        if (!cancelled) setError(err.response?.data?.detail || t('common.error'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [id, t])

  if (loading) {
    return (
      <div className="page report-page">
        <div className="report-loading">
          <div className="progress-spinner" />
          <p>{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="page report-page">
        <div className="report-loading">
          <p className="text-error">{error || t('contracts.reportUnavailable')}</p>
          <button className="btn btn-secondary" onClick={() => navigate('/contracts')}>
            {t('common.back')}
          </button>
        </div>
      </div>
    )
  }

  if (recordType === 'comparison') {
    return (
      <CompareResult
        report={report as CompareReport}
        onReset={() => navigate('/contracts')}
      />
    )
  }

  return (
    <AnalysisResult
      report={report as AnalysisReport}
      contractId={Number(id)}
      fileName={fileName}
      onBack={() => navigate('/contracts')}
    />
  )
}
