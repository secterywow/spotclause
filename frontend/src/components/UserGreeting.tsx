import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'

interface UserGreetingProps {
  variant: 'review' | 'compare'
}

function getTimeKey(): 'morning' | 'afternoon' | 'evening' {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 18) return 'afternoon'
  return 'evening'
}

export default function UserGreeting({ variant }: UserGreetingProps) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const timeKey = getTimeKey()
  const name = user?.name || (user?.email ? user.email.split('@')[0] : t('common.user'))

  return (
    <div className="user-greeting">
      <div className="user-greeting-text">
        <h1 className="user-greeting-title">
          {t(`greeting.${timeKey}`)}, <em className="serif-italic">{name}</em>
        </h1>
        <p className="user-greeting-subtitle">
          {variant === 'review' ? t('greeting.reviewSubtitle') : t('greeting.compareSubtitle')}
        </p>
      </div>
      <div className="user-greeting-decor" aria-hidden>
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <circle cx="40" cy="40" r="32" stroke="currentColor" strokeWidth="1.4" strokeDasharray="3 5" opacity="0.4" />
          <circle cx="40" cy="40" r="22" stroke="currentColor" strokeWidth="1.4" opacity="0.6" />
          <path d="M28 40 L36 48 L52 32" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  )
}
