import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import ThemeToggle from './ThemeToggle'
import LanguageSwitcher from './LanguageSwitcher'

interface NavbarProps {
  onLoginClick: () => void
  onRegisterClick: () => void
}

export default function Navbar({ onLoginClick, onRegisterClick }: NavbarProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const navItems = [
    { path: '/', label: t('nav.review') },
    { path: '/compare', label: t('nav.compare') },
    { path: '/pricing', label: t('nav.pricing') },
  ]

  return (
    <nav className="navbar">
      <button className="navbar-menu-btn" onClick={() => setMenuOpen(!menuOpen)} aria-label="Menu">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div className="navbar-brand">
        <Link to="/" className="logo">
          <span className="logo-icon">&#9878;</span>
          <span className="logo-text">SpotClause</span>
        </Link>
      </div>

      <div className={`navbar-nav ${menuOpen ? 'open' : ''}`}>
        {navItems.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => setMenuOpen(false)}
          >
            {item.label}
          </Link>
        ))}
        <div className="navbar-menu-actions">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </div>

      <div className="navbar-actions">
        <div className="navbar-actions-desktop">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
        <button className="btn btn-outline btn-sm" onClick={onLoginClick}>
          {t('auth.login')}
        </button>
        <button className="btn btn-primary btn-sm" onClick={onRegisterClick}>
          Start
        </button>
      </div>
    </nav>
  )
}
