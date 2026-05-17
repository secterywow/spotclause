from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.utils.security import decode_access_token
from app.logger import get_logger
import os

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter(prefix="/api/dodo", tags=["dodo"])

# Auth dependency: extract user from Bearer token
def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Lazy import to avoid startup error if SDK not installed
def get_dodo_client():
    try:
        from dodopayments import DodoPayments
    except ImportError:
        raise HTTPException(status_code=500, detail="Dodo Payments SDK not installed")

    if not settings.dodo_payments_api_key:
        raise HTTPException(status_code=500, detail="Dodo Payments API key not configured")

    env = "test_mode" if settings.debug else "live_mode"
    return DodoPayments(bearer_token=settings.dodo_payments_api_key, environment=env)


class CreatePaymentRequest(BaseModel):
    product_id: str
    billing_cycle: str = "monthly"  # monthly or yearly


@router.post("/create-payment")
def create_payment(
    req: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Dodo Payments checkout link for subscription."""
    client = get_dodo_client()

    # Map product_id to Dodo product ID
    # For now we only have one test product for Standard monthly
    product_id = req.product_id

    try:
        logger.info("Creating Dodo checkout session", product_id=product_id, user_email=current_user.email)
        session = client.checkout_sessions.create(
            product_cart=[
                {
                    "product_id": product_id,
                    "quantity": 1,
                }
            ],
        )
        logger.info("Dodo checkout session created", checkout_url=session.checkout_url)
        return {"payment_link": session.checkout_url}
    except Exception as e:
        logger.error("Failed to create Dodo checkout session", error=str(e), product_id=product_id)
        raise HTTPException(status_code=400, detail=f"Failed to create payment: {str(e)}")


@router.post("/webhook")
def dodo_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Dodo Payments webhooks."""
    payload = request.body()

    # TODO: Verify webhook signature when Dodo provides webhook secret support
    # For now, just parse and handle the event

    import json
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type", "")

    if event_type == "payment.succeeded":
        data = event.get("data", {}).get("object", {})
        customer_email = data.get("customer", {}).get("email", "")
        # TODO: Update user subscription in database
        # Find user by email and upgrade plan
        pass
    elif event_type == "subscription.created":
        # TODO: Handle subscription creation
        pass
    elif event_type == "subscription.cancelled":
        # TODO: Handle subscription cancellation
        pass

    return {"status": "success"}
