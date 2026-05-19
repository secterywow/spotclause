import { Helmet } from 'react-helmet-async'

export default function RefundPolicy() {
  return (
    <div className="page legal-page">
      <Helmet>
        <title>Refund Policy - SpotClause</title>
        <meta name="description" content="SpotClause refund policy. Learn about our 7-day money-back guarantee." />
        <link rel="canonical" href="https://spotclause.app/refund" />
      </Helmet>
      <div className="legal-container">
        <h1>Refund Policy</h1>
        <p className="legal-updated">Last updated: May 14, 2025</p>

        <section>
          <h2>1. Overview</h2>
          <p>We want you to be satisfied with SpotClause. If you are not happy with your subscription, we offer refunds under the conditions outlined below.</p>
        </section>

        <section>
          <h2>2. Eligibility for Refunds</h2>
          <p>You are eligible for a full refund if:</p>
          <ul>
            <li>You request a refund within <strong>7 days</strong> of your initial purchase</li>
            <li>You have used <strong>less than 20%</strong> of your monthly quota</li>
            <li>This is your <strong>first subscription</strong> with us</li>
          </ul>
          <p>Refund requests must be sent to javuxitedo792@gmail.com with your account email and purchase details.</p>
        </section>

        <section>
          <h2>3. Non-Refundable Situations</h2>
          <p>Refunds will not be granted if:</p>
          <ul>
            <li>The refund request is made more than 7 days after purchase</li>
            <li>You have used more than 20% of your monthly quota</li>
            <li>You have previously received a refund for a SpotClause subscription</li>
            <li>The refund is requested due to violation of our Terms of Service</li>
          </ul>
        </section>

        <section>
          <h2>4. Processing Time</h2>
          <p>Approved refunds are processed within 5-10 business days. The refund will be credited to your original payment method.</p>
        </section>

        <section>
          <h2>5. Cancellation</h2>
          <p>You can cancel your subscription at any time from your Settings page. Cancellation takes effect at the end of your current billing period. You will continue to have access until the period ends, but no refund will be issued for the remaining time.</p>
        </section>

        <section>
          <h2>6. Contact</h2>
          <p>For refund requests or questions, contact us at: javuxitedo792@gmail.com</p>
        </section>
      </div>
    </div>
  )
}
