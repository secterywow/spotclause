import { useTranslation } from 'react-i18next'
import {
  RiskAnalysisIllustration, JurisdictionIllustration, NegotiationIllustration,
  PlainLanguageIllustration, SpeedIllustration, PrivacyIllustration,
  CompareIllustration, TrapIllustration, BarChartIllustration, LayoutIllustration,
} from './Illustrations'

interface SEOContentProps {
  variant?: 'review' | 'compare'
}

// Minimal line icons for the step module (simple geometric, single stroke)
const StepUploadIcon = ({ size = 42 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
)

const StepAnalyzeIcon = ({ size = 42 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
    <line x1="11" y1="8" x2="11" y2="14" />
    <line x1="8" y1="11" x2="14" y2="11" />
  </svg>
)

const StepReportIcon = ({ size = 42 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <polyline points="9 15 11 17 15 13" />
  </svg>
)

export default function SEOContent({ variant = 'review' }: SEOContentProps) {
  const { t } = useTranslation()

  const reviewFeatures = [
    { Icon: RiskAnalysisIllustration, key: 'reviewFeature1' },
    { Icon: JurisdictionIllustration, key: 'reviewFeature2' },
    { Icon: NegotiationIllustration, key: 'reviewFeature3' },
    { Icon: PlainLanguageIllustration, key: 'reviewFeature4' },
    { Icon: SpeedIllustration, key: 'reviewFeature5' },
    { Icon: PrivacyIllustration, key: 'reviewFeature6' },
  ]

  const compareFeatures = [
    { Icon: CompareIllustration, key: 'compareFeature1' },
    { Icon: TrapIllustration, key: 'compareFeature2' },
    { Icon: BarChartIllustration, key: 'compareFeature3' },
    { Icon: LayoutIllustration, key: 'compareFeature4' },
  ]

  const features = variant === 'compare' ? compareFeatures : reviewFeatures

  // Scenarios: both review and compare share the same scenario images
  const scenarios = [
    { image: '/scenarios/1.jpg', key: 'scenario1' },
    { image: '/scenarios/2.jpg', key: 'scenario2' },
    { image: '/scenarios/3.jpg', key: 'scenario3' },
    { image: '/scenarios/4.jpg', key: 'scenario4' },
    { image: '/scenarios/5.jpg', key: 'scenario5' },
    { image: '/scenarios/6.jpg', key: 'scenario6' },
  ]

  const faqs = [1, 2, 3, 4]

  return (
    <div className="seo-content">
      {/* Features */}
      <section className="seo-features">
        <div className="section-header">
          <h2 className="section-title">
            {t('seo.featuresTitle')}
          </h2>
          <p className="section-subtitle">{t('seo.featuresSubtitle')}</p>
        </div>
        <div className="features-grid">
          {features.map((f, i) => (
            <div key={i} className="feature-card">
              <div className="feature-icon-box">
                <f.Icon size={36} />
              </div>
              <h3>{t(`seo.${f.key}Title`)}</h3>
              <p>{t(`seo.${f.key}Desc`)}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Scenarios with images */}
      <section className="seo-scenarios">
        <div className="section-header">
          <h2 className="section-title">
            {t('seo.scenariosTitle')}
          </h2>
          <p className="section-subtitle">{t('seo.scenariosSubtitle')}</p>
        </div>
        <div className="scenarios-grid">
          {scenarios.map((s, i) => (
            <div key={i} className="scenario-card-image">
              <div className="scenario-image-wrap">
                {s.image ? (
                  <img src={s.image} alt={t(`seo.${s.key}Title`)} loading="lazy" />
                ) : (
                  <div className="scenario-image-placeholder">
                    <span>Image {i + 1}</span>
                  </div>
                )}
              </div>
              <div className="scenario-text">
                <h3>{t(`seo.${s.key}Title`)}</h3>
                <p>{t(`seo.${s.key}Desc`)}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="seo-howit">
        <div className="section-header">
          <h2 className="section-title">
            {t('seo.howitTitle')}
          </h2>
          <p className="section-subtitle">{t('seo.howitSubtitle')}</p>
        </div>
        <div className="steps-grid">
          <div className="step-item">
            <div className="step-icon-wrap">
              <StepUploadIcon size={36} />
            </div>
            <div className="step-num-badge">01</div>
            <h3>{t('seo.step1Title')}</h3>
            <p>{t('seo.step1Desc')}</p>
          </div>
          <div className="step-item">
            <div className="step-icon-wrap">
              <StepAnalyzeIcon size={36} />
            </div>
            <div className="step-num-badge">02</div>
            <h3>{t('seo.step2Title')}</h3>
            <p>{t('seo.step2Desc')}</p>
          </div>
          <div className="step-item">
            <div className="step-icon-wrap">
              <StepReportIcon size={36} />
            </div>
            <div className="step-num-badge">03</div>
            <h3>{t('seo.step3Title')}</h3>
            <p>{t('seo.step3Desc')}</p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="seo-faq">
        <div className="section-header">
          <h2 className="section-title">
            {t('seo.faqTitle')}
          </h2>
          <p className="section-subtitle">{t('seo.faqSubtitle')}</p>
        </div>
        <div className="faq-list">
          {faqs.map((i) => (
            <details key={i} className="faq-item">
              <summary>{t(`seo.faq${i}Q`)}</summary>
              <p>{t(`seo.faq${i}A`)}</p>
            </details>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="seo-cta">
        <h2 className="section-title">
          {t('seo.ctaTitlePrefix')} <em className="serif-italic">{t('seo.ctaTitleItalic')}</em> {t('seo.ctaTitleSuffix')}
        </h2>
        <p>{t('seo.ctaSubtitle')}</p>
      </section>
    </div>
  )
}
