import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ThemeToggle from './ThemeToggle'
import LanguageSwitcher from './LanguageSwitcher'

interface NavbarProps {
  onLoginClick: () => void
}

export default function Navbar({ onLoginClick }: NavbarProps) {
  const { t } = useTranslation()
  const location = useLocation()

  const navItems = [
    { path: '/', label: t('nav.review') },
    { path: '/compare', label: t('nav.compare') },
    { path: '/pricing', label: t('nav.pricing') },
  ]

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="logo">
          <span className="logo-icon">&#9878;</span>
          <span className="logo-text">SpotClause</span>
        </Link>
      </div>
      <div className="navbar-nav">
        {navItems.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
          >
            {item.label}
          </Link>
        ))}
      </div>
      <div className="navbar-actions">
        <LanguageSwitcher />
        <ThemeToggle />
        <button className="btn btn-primary" onClick={onLoginClick}>
          {t('auth.login')}
        </button>
      </div>
    </nav>
  )
}
