import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { useToast } from '../hooks/useToast'
import { api } from '../lib/api'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SubscriptionModal from '../components/SubscriptionModal'

const PLAN_LABEL: Record<string, string> = {
  free: 'plans.free',
  standard: 'plans.standard',
  pro: 'plans.pro',
}

interface UsageInfo {
  limit: number
  used: number
  remaining: number
}

interface UsageData {
  plan: string
  month: string
  analyze: UsageInfo
  compare: UsageInfo
}

export default function Settings() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [busy, setBusy] = useState(false)
  const [usage, setUsage] = useState<UsageData | null>(null)
  const [showSubModal, setShowSubModal] = useState(false)

  useEffect(() => {
    if (!user) return
    api.get(`/api/contracts/usage/${user.id}`)
      .then(res => setUsage(res.data))
      .catch(() => setUsage(null))
  }, [user])

  if (!user) return null

  const planKey = PLAN_LABEL[user.plan] || PLAN_LABEL.free
  const isFree = user.plan === 'free'

  const initials = (user.name || user.email || '?').slice(0, 2).toUpperCase()

  const handleDeleteAccount = async () => {
    setBusy(true)
    try {
      await api.delete(`/api/auth/account?user_id=${user.id}`)
      showToast(t('settings.accountDeleted'), 'success')
      logout()
      navigate('/')
    } catch (err: any) {
      showToast(err.response?.data?.detail || t('settings.deleteFailed'), 'error')
    } finally {
      setBusy(false)
      setConfirmingDelete(false)
    }
  }

  return (
    <div className="page settings-page">
      <div className="settings-header">
        <h1>{t('settings.title')}</h1>
        <p className="text-muted">{t('settings.subtitle')}</p>
      </div>

      {/* Profile */}
      <section className="settings-card">
        <div className="settings-card-head">
          <h3>{t('settings.profile')}</h3>
        </div>
        <div className="settings-profile">
          <div className="profile-avatar" aria-hidden>
            {user.avatar ? (
              <img src={user.avatar} alt={user.name || user.email} />
            ) : (
              <span>{initials}</span>
            )}
          </div>
          <div className="profile-info">
            <div className="profile-name">{user.name || t('settings.unnamedUser')}</div>
            <div className="profile-email">{user.email}</div>
            <div className="profile-meta">
              <span className={`plan-badge plan-${user.plan}`}>{t(planKey)}</span>
              {user.role === 'admin' && <span className="role-badge">{t('settings.admin')}</span>}
            </div>
          </div>
        </div>
      </section>

      {/* Usage Stats */}
      {usage && (
        <section className="settings-card">
          <div className="settings-card-head">
            <h3>{t('settings.usageStats')}</h3>
          </div>
          <div className="settings-usage">
            <div className="usage-row">
              <div className="usage-label">{t('settings.analyzeUsage')}</div>
              <div className="usage-bar-wrap">
                <div
                  className="usage-bar"
                  style={{
                    width: `${usage.analyze.limit > 0 ? (usage.analyze.used / usage.analyze.limit) * 100 : 0}%`,
                  }}
                />
              </div>
              <div className="usage-text">
                {usage.analyze.used} / {usage.analyze.limit}
              </div>
            </div>
            <div className="usage-row">
              <div className="usage-label">{t('settings.compareUsage')}</div>
              <div className="usage-bar-wrap">
                <div
                  className="usage-bar"
                  style={{
                    width: `${usage.compare.limit > 0 ? (usage.compare.used / usage.compare.limit) * 100 : 0}%`,
                  }}
                />
              </div>
              <div className="usage-text">
                {usage.compare.used} / {usage.compare.limit}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Subscription */}
      {isFree && (
        <section className="settings-card">
          <div className="settings-card-head">
            <h3>{t('settings.subscription')}</h3>
          </div>
          <div className="settings-row">
            <div className="row-text">
              <div className="row-title">{t('settings.currentPlan')}</div>
              <div className="row-desc">{t('settings.freeDesc')}</div>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => setShowSubModal(true)}
            >
              {t('settings.upgrade')}
            </button>
          </div>
        </section>
      )}

      {/* Preferences */}
      <section className="settings-card">
        <div className="settings-card-head">
          <h3>{t('settings.preferences')}</h3>
        </div>
        <div className="settings-row">
          <div className="row-text">
            <div className="row-title">{t('settings.theme')}</div>
            <div className="row-desc">{t('settings.themeDesc')}</div>
          </div>
          <button className="btn btn-ghost" onClick={toggleTheme}>
            {theme === 'dark' ? t('settings.themeLight') : t('settings.themeDark')}
          </button>
        </div>
        <div className="settings-row">
          <div className="row-text">
            <div className="row-title">{t('settings.language')}</div>
            <div className="row-desc">{t('settings.languageDesc')}</div>
          </div>
          <LanguageSwitcher />
        </div>
      </section>

      {/* Security */}
      <section className="settings-card">
        <div className="settings-card-head">
          <h3>{t('settings.security')}</h3>
        </div>
        <div className="settings-row">
          <div className="row-text">
            <div className="row-title">{t('settings.signOut')}</div>
            <div className="row-desc">{t('settings.signOutDesc')}</div>
          </div>
          <button className="btn btn-ghost" onClick={() => { logout(); navigate('/') }}>
            {t('auth.logout')}
          </button>
        </div>
        <div className="settings-row danger">
          <div className="row-text">
            <div className="row-title">{t('settings.deleteAccount')}</div>
            <div className="row-desc">{t('settings.deleteAccountDesc')}</div>
          </div>
          {confirmingDelete ? (
            <div className="confirm-cluster">
              <button
                className="btn btn-danger btn-sm"
                disabled={busy}
                onClick={handleDeleteAccount}
              >
                {t('settings.confirmDelete')}
              </button>
              <button
                className="btn btn-ghost btn-sm"
                disabled={busy}
                onClick={() => setConfirmingDelete(false)}
              >
                {t('common.cancel')}
              </button>
            </div>
          ) : (
            <button className="btn btn-danger" onClick={() => setConfirmingDelete(true)}>
              {t('settings.deleteAccount')}
            </button>
          )}
        </div>
      </section>

      {/* About */}
      <section className="settings-card">
        <div className="settings-card-head">
          <h3>{t('settings.about')}</h3>
        </div>
        <div className="settings-about">
          <p className="text-muted">{t('settings.aboutDesc')}</p>
          <div className="about-links">
            <a href="/privacy">{t('footer.privacy')}</a>
            <a href="/terms">{t('footer.terms')}</a>
            <a href="/disclaimer">{t('footer.disclaimer')}</a>
            <a href="mailto:javuxitedo792@gmail.com">{t('settings.support')}</a>
          </div>
        </div>
      </section>

      {showSubModal && (
        <SubscriptionModal
          reason={t('settings.upgradePrompt')}
          onClose={() => setShowSubModal(false)}
        />
      )}
    </div>
  )
}
