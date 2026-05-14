import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export default function Footer() {
  const { t } = useTranslation()

  return (
    <footer className="site-footer">
      <div className="footer-container">
        <div className="footer-brand">
          <Link to="/" className="footer-logo">
            <span className="footer-logo-text">SpotClause</span>
          </Link>
          <p className="footer-tagline">{t('footer.tagline')}</p>
        </div>

        <div className="footer-links">
          <div className="footer-col">
            <h4>{t('footer.product')}</h4>
            <Link to="/">{t('footer.productReview')}</Link>
            <Link to="/compare">{t('footer.productCompare')}</Link>
            <Link to="/pricing">{t('footer.productPricing')}</Link>
          </div>

          <div className="footer-col">
            <h4>{t('footer.legal')}</h4>
            <Link to="/privacy">{t('footer.privacy')}</Link>
            <Link to="/terms">{t('footer.terms')}</Link>
            <Link to="/refund">{t('footer.refund')}</Link>
            <Link to="/disclaimer">{t('footer.disclaimer')}</Link>
          </div>

          <div className="footer-col">
            <h4>{t('footer.support')}</h4>
            <a href="mailto:javuxitedo792@gmail.com">{t('footer.contact')}</a>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <p>{t('footer.copyright', { year: new Date().getFullYear() })}</p>
        <p className="footer-disclaimer">
          {t('footer.legalNotice')}
        </p>
      </div>
    </footer>
  )
}
