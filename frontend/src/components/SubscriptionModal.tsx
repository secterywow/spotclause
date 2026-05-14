import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'

interface PricingPlan {
  name: string
  price_monthly: number
  price_yearly: number
  features: Record<string, any>
}

interface PricingData {
  country_code: string
  region_name: string
  currency: string
  plans: {
    free: PricingPlan
    standard: PricingPlan
    pro: PricingPlan
  }
}

interface Props {
  reason: string
  onClose: () => void
}

export default function SubscriptionModal({ reason, onClose }: Props) {
  const { t } = useTranslation()
  const { user: _user } = useAuth()
  const [isYearly, setIsYearly] = useState(false)
  const [pricing, setPricing] = useState<PricingData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/pricing/detect')
      .then(res => setPricing(res.data))
      .catch(() => setPricing(null))
      .finally(() => setLoading(false))
  }, [])

  const formatPrice = (price: number, currency: string) => {
    if (price === 0) return '$0'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(price)
  }

  const plans = pricing?.plans || {
    free: { name: 'Free', price_monthly: 0, price_yearly: 0, features: { analyze: '1', compare: '1', follow_up: false, export: false, negotiation: false, deadline: false, loophole: false, risk_edit: false } },
    standard: { name: 'Standard', price_monthly: 12.90, price_yearly: 10.32, features: { analyze: '10 per month', compare: '10 per month', follow_up: true, export: true, negotiation: true, deadline: true, loophole: true, risk_edit: true } },
    pro: { name: 'Pro', price_monthly: 24.90, price_yearly: 19.92, features: { analyze: '50 per month', compare: '50 per month', follow_up: true, export: true, negotiation: true, deadline: true, loophole: true, risk_edit: true } },
  }

  const currency = pricing?.currency || 'USD'

  const planList = [
    { key: 'standard', plan: plans.standard, popular: true },
    { key: 'pro', plan: plans.pro, popular: false },
  ]

  const renderFeatures = (plan: PricingPlan, key: string) => {
    const f = plan.features
    if (key === 'free') {
      return [
        { label: t('pricing.analyzeContracts'), value: t('pricing.countTimes', { count: f.analyze }), ok: true },
        { label: t('pricing.compareContracts'), value: t('pricing.countTimes', { count: f.compare }), ok: true },
      ]
    }
    return [
      { label: t('pricing.analyzeContracts'), value: f.analyze, ok: true },
      { label: t('pricing.compareContracts'), value: f.compare, ok: true },
      { label: t('pricing.followUp'), value: '', ok: f.follow_up },
      { label: t('pricing.exportFormats'), value: '', ok: f.export },
      { label: t('pricing.negotiation'), value: '', ok: f.negotiation },
      { label: t('pricing.deadline'), value: '', ok: f.deadline },
      { label: t('pricing.loophole'), value: '', ok: f.loophole },
      { label: t('pricing.riskEdit'), value: '', ok: f.risk_edit },
    ]
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content subscription-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2>{t('subscription.title')}</h2>
            <p className="subscription-reason">{reason}</p>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="subscription-body">
          <div className="pricing-toggle subscription-toggle">
            <button className={`toggle-btn ${!isYearly ? 'active' : ''}`} onClick={() => setIsYearly(false)}>
              {t('pricing.monthly')}
            </button>
            <button className={`toggle-btn ${isYearly ? 'active' : ''}`} onClick={() => setIsYearly(true)}>
              {t('pricing.yearly')}
              <span className="toggle-badge">{t('pricing.save', { percent: 20 })}</span>
            </button>
          </div>

          {loading ? (
            <div className="subscription-loading">{t('common.loading')}</div>
          ) : (
            <div className="subscription-plans">
              {planList.map(({ key, plan, popular }) => (
                <div key={key} className={`pricing-card ${popular ? 'popular' : ''}`}>
                  {popular && <div className="popular-badge">{t('pricing.popular')}</div>}
                  <h3>{t(`pricing.${key}`)}</h3>
                  <div className="pricing-price">
                    <span className="price-amount">
                      {formatPrice(isYearly ? plan.price_yearly : plan.price_monthly, currency)}
                    </span>
                    <span className="price-period">{t('pricing.perMonth')}</span>
                  </div>
                  <ul className="pricing-features">
                    {renderFeatures(plan, key).map((feat, i) => (
                      <li key={i}>
                        <span className={`feature-check ${feat.ok ? '' : 'disabled'}`}>
                          {feat.ok ? '✓' : '×'}
                        </span>
                        {feat.label}{feat.value ? `: ${feat.value}` : ''}
                      </li>
                    ))}
                  </ul>
                  <button
                    className={`btn ${popular ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={onClose}
                  >
                    {t('pricing.upgrade')}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
