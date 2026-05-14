import { useTranslation } from 'react-i18next'
import { supportedLanguages } from '../i18n'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const currentLang = i18n.language

  const handleChange = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('spotclause-language', code)
    const lang = supportedLanguages.find(l => l.code === code)
    if (lang) {
      document.documentElement.dir = lang.dir
      document.documentElement.lang = code
    }
  }

  return (
    <select
      className="language-select"
      value={currentLang}
      onChange={(e) => handleChange(e.target.value)}
    >
      {supportedLanguages.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.name}
        </option>
      ))}
    </select>
  )
}
