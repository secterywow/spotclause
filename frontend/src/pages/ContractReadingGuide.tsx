import { Helmet } from 'react-helmet-async'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export default function ContractReadingGuide() {
  const { t } = useTranslation()

  const sections = [
    {
      title: t('guide.section1Title'),
      items: [
        t('guide.section1Item1'),
        t('guide.section1Item2'),
        t('guide.section1Item3'),
        t('guide.section1Item4'),
      ],
    },
    {
      title: t('guide.section2Title'),
      items: [
        t('guide.section2Item1'),
        t('guide.section2Item2'),
        t('guide.section2Item3'),
        t('guide.section2Item4'),
      ],
    },
    {
      title: t('guide.section3Title'),
      items: [
        t('guide.section3Item1'),
        t('guide.section3Item2'),
        t('guide.section3Item3'),
        t('guide.section3Item4'),
      ],
    },
    {
      title: t('guide.section4Title'),
      items: [
        t('guide.section4Item1'),
        t('guide.section4Item2'),
        t('guide.section4Item3'),
        t('guide.section4Item4'),
      ],
    },
    {
      title: t('guide.section5Title'),
      items: [
        t('guide.section5Item1'),
        t('guide.section5Item2'),
        t('guide.section5Item3'),
        t('guide.section5Item4'),
      ],
    },
    {
      title: t('guide.section6Title'),
      items: [
        t('guide.section6Item1'),
        t('guide.section6Item2'),
        t('guide.section6Item3'),
        t('guide.section6Item4'),
      ],
    },
  ]

  return (
    <div className="page guide-page">
      <Helmet>
        <title>{t('guide.pageTitle')}</title>
        <meta name="description" content={t('guide.metaDescription')} />
        <link rel="canonical" href="https://spotclause.app/contract-reading-guide" />
      </Helmet>

      <div className="guide-container">
        <h1>{t('guide.h1')}</h1>
        <p className="guide-intro">{t('guide.intro')}</p>

        {sections.map((section, index) => (
          <section key={index} className="guide-section">
            <h2>{section.title}</h2>
            <ul>
              {section.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </section>
        ))}

        <section className="guide-section guide-cta">
          <h2>{t('guide.ctaTitle')}</h2>
          <p>{t('guide.ctaDescription')}</p>
          <div className="guide-cta-buttons">
            <Link to="/" className="btn btn-primary">
              {t('guide.ctaRead')}
            </Link>
            <Link to="/compare" className="btn btn-outline">
              {t('guide.ctaCompare')}
            </Link>
          </div>
        </section>
      </div>
    </div>
  )
}
