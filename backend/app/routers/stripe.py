from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
import stripe as stripe_lib

settings = get_settings()
router = APIRouter(prefix="/api/stripe", tags=["stripe"])

# Initialize Stripe
stripe_lib.api_key = settings.stripe_secret_key


@router.post("/create-subscription")
def create_subscription(plan: str, billing_cycle: str, db: Session = Depends(get_db)):
    """Create a Stripe checkout session for subscription."""
    # TODO: Implement Stripe checkout session creation
    # This is a placeholder for the actual Stripe integration
    return {"message": "Stripe integration pending", "plan": plan, "billing_cycle": billing_cycle}


@router.post("/webhook")
def stripe_webhook(request: Request, db: Session = Depends(get_db), stripe_signature: str = Header(None, alias="Stripe-Signature")):
    """Handle Stripe webhooks."""
    payload = request.body()

    try:
        event = stripe_lib.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe_lib.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # TODO: Update user subscription in database
        pass
    elif event['type'] == 'invoice.payment_failed':
        # TODO: Handle payment failure
        pass
    elif event['type'] == 'customer.subscription.deleted':
        # TODO: Handle subscription cancellation
        pass

    return {"status": "success"}


@router.post("/cancel")
def cancel_subscription(db: Session = Depends(get_db)):
    """Cancel user subscription."""
    # TODO: Implement subscription cancellation
    return {"message": "Cancellation pending"}
