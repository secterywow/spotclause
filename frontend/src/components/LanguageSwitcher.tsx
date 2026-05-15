import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { supportedLanguages } from '../i18n'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const currentLang = i18n.language
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const current = supportedLanguages.find(l => l.code === currentLang) || supportedLanguages[0]

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleChange = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('spotclause-language', code)
    const lang = supportedLanguages.find(l => l.code === code)
    if (lang) {
      document.documentElement.dir = lang.dir
      document.documentElement.lang = code
    }
    setOpen(false)
  }

  return (
    <div className="language-switcher" ref={ref}>
      <button className="language-switcher-trigger" onClick={() => setOpen(!open)}>
        <span>{current.code.toUpperCase()}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <div className="language-switcher-dropdown">
          {supportedLanguages.map((lang) => (
            <button
              key={lang.code}
              className={`language-switcher-option ${lang.code === currentLang ? 'active' : ''}`}
              onClick={() => handleChange(lang.code)}
            >
              <span className="lang-code">{lang.code.toUpperCase()}</span>
              <span className="lang-name">{lang.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
