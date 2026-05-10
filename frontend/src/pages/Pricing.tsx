import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'

interface PricingPlan {
  name: string
  price_monthly: number
  price_yearly: number
  features: {
    analyze: string
    compare: string
    follow_up: boolean
    export: boolean
  }
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

export default function Pricing() {
  const { t } = useTranslation()
  const { isLoggedIn, user } = useAuth()
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
    free: { name: 'Free', price_monthly: 0, price_yearly: 0, features: { analyze: '1 lifetime (1MB limit)', compare: '0', follow_up: false, export: true } },
    standard: { name: 'Standard', price_monthly: 12.90, price_yearly: 10.32, features: { analyze: '10 per month', compare: '10 per month', follow_up: true, export: true } },
    pro: { name: 'Pro', price_monthly: 24.90, price_yearly: 19.92, features: { analyze: '50 per month', compare: '50 per month', follow_up: true, export: true } },
  }

  const currency = pricing?.currency || 'USD'

  const planList = [
    { key: 'free', plan: plans.free, popular: false },
    { key: 'standard', plan: plans.standard, popular: true },
    { key: 'pro', plan: plans.pro, popular: false },
  ]

  if (loading) {
    return (
      <div className="page pricing-page">
        <div className="pricing-loading">{t('common.loading')}</div>
      </div>
    )
  }

  return (
    <div className="page pricing-page">
      <div className="pricing-header">
        <h1>{t('pricing.title')}</h1>
        <p className="pricing-subtitle">{t('pricing.subtitle')}</p>

        <div className="pricing-toggle">
          <button
            className={`toggle-btn ${!isYearly ? 'active' : ''}`}
            onClick={() => setIsYearly(false)}
          >
            {t('pricing.monthly')}
          </button>
          <button
            className={`toggle-btn ${isYearly ? 'active' : ''}`}
            onClick={() => setIsYearly(true)}
          >
            {t('pricing.yearly')}
            <span className="toggle-badge">{t('pricing.save', { percent: 20 })}</span>
          </button>
        </div>
      </div>

      <div className="pricing-grid">
        {planList.map(({ key, plan, popular }) => (
          <div
            key={key}
            className={`pricing-card ${popular ? 'popular' : ''} ${user?.plan === key ? 'current' : ''}`}
          >
            {popular && <div className="popular-badge">Popular</div>}
            {user?.plan === key && <div className="current-badge">{t('pricing.currentPlan')}</div>}

            <h3>{t(`pricing.${key}`)}</h3>
            <div className="pricing-price">
              <span className="price-amount">
                {formatPrice(isYearly ? plan.price_yearly : plan.price_monthly, currency)}
              </span>
              <span className="price-period">{t('pricing.perMonth')}</span>
            </div>

            <ul className="pricing-features">
              <li>
                <span className="feature-check">✓</span>
                {t('pricing.analyzeContracts')}: {plan.features.analyze}
              </li>
              <li>
                <span className="feature-check">✓</span>
                {t('pricing.compareContracts')}: {plan.features.compare}
              </li>
              <li>
                <span className={`feature-check ${plan.features.follow_up ? '' : 'disabled'}`}>
                  {plan.features.follow_up ? '✓' : '×'}
                </span>
                {t('pricing.followUp')}
              </li>
              <li>
                <span className={`feature-check ${plan.features.export ? '' : 'disabled'}`}>
                  {plan.features.export ? '✓' : '×'}
                </span>
                {t('pricing.export')}
              </li>
            </ul>

            <button
              className={`btn ${popular ? 'btn-primary' : 'btn-secondary'}`}
              disabled={key === 'free' || user?.plan === key}
            >
              {key === 'free'
                ? t('pricing.getStarted')
                : user?.plan === key
                  ? t('pricing.currentPlan')
                  : t('pricing.upgrade')}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
