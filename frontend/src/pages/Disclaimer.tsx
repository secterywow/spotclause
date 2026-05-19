import { Helmet } from 'react-helmet-async'

export default function Disclaimer() {
  return (
    <div className="page legal-page">
      <Helmet>
        <title>Disclaimer - SpotClause</title>
        <meta name="description" content="SpotClause disclaimer. Our AI-generated analysis is for informational purposes only and does not constitute professional advice." />
        <link rel="canonical" href="https://spotclause.app/disclaimer" />
      </Helmet>
      <h1>Disclaimer</h1>
      <p>
        SpotClause AI is a software application. The output
        provided is generated automatically by software algorithms and is for
        informational purposes only. It does not constitute professional advice
        or any regulated service. For important decisions,
        please consult a qualified professional.
      </p>
    </div>
  )
}
