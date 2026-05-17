from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.subscription import Subscription
from app.models.payment import PendingPayment
from app.utils.security import decode_access_token
from app.logger import get_logger
import os

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter(prefix="/api/dodo", tags=["dodo"])

# Product ID mapping for Live mode
# Standard monthly: pdt_0NesPfHczx0qkBIHmdNYp
# Standard yearly:  pdt_0Nf1qULHW39PsCeW4pER7
# Pro monthly:      pdt_0Nf1qaixwqgs3Z6FMIE38
# Pro yearly:       pdt_0Nf1qeKGi6aR7sUILOAN4
PRODUCT_IDS = {
    "standard": {
        "monthly": "pdt_0NesPfHczx0qkBIHmdNYp",
        "yearly": "pdt_0Nf1qULHW39PsCeW4pER7",
    },
    "pro": {
        "monthly": "pdt_0Nf1qaixwqgs3Z6FMIE38",
        "yearly": "pdt_0Nf1qeKGi6aR7sUILOAN4",
    },
}

PLAN_DURATIONS = {
    "monthly": 30,
    "yearly": 365,
}


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
    plan: str
    billing_cycle: str = "monthly"


@router.post("/create-payment")
def create_payment(
    req: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Dodo Payments checkout link for subscription."""
    client = get_dodo_client()

    plan = req.plan.lower()
    cycle = req.billing_cycle.lower()

    product_id = PRODUCT_IDS.get(plan, {}).get(cycle)
    if not product_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan or billing cycle: {plan}/{cycle}")

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
        checkout_url = session.checkout_url
        session_id = getattr(session, "id", None)

        # Track pending payment so the webhook can map back to this user
        pending = PendingPayment(
            user_id=current_user.id,
            plan=plan,
            billing_cycle=cycle,
            checkout_session_id=session_id,
            status="pending",
        )
        db.add(pending)
        db.commit()

        logger.info("Dodo checkout session created", checkout_url=checkout_url, session_id=session_id)
        return {"payment_link": checkout_url}
    except Exception as e:
        logger.error("Failed to create Dodo checkout session", error=str(e), product_id=product_id)
        raise HTTPException(status_code=400, detail=f"Failed to create payment: {str(e)}")


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

async def _parse_webhook_payload(request: Request) -> dict:
    """Safely read and parse the webhook body."""
    body = await request.body()
    import json
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


def _extract_checkout_id(event: dict) -> str | None:
    """Try several common payload shapes to find a checkout/session id."""
    # Shape 1: payment.succeeded → data.object.checkout_session_id
    data = event.get("data", {}).get("object", {})
    for key in ("checkout_session_id", "session_id", "id", "checkout_id"):
        val = data.get(key)
        if val:
            return str(val)
    # Shape 2: subscription.created → data.object.id
    sub = data.get("subscription", {}) or data
    for key in ("checkout_session_id", "session_id", "id"):
        val = sub.get(key)
        if val:
            return str(val)
    return None


def _extract_customer_email(event: dict) -> str | None:
    """Extract customer email from the webhook payload."""
    data = event.get("data", {}).get("object", {})
    customer = data.get("customer", {})
    email = customer.get("email", "")
    if email:
        return email
    # Fallback: some providers put email at top level
    return data.get("customer_email") or data.get("email")


def _upgrade_user_plan(db: Session, user_id: int, plan: str, billing_cycle: str) -> None:
    """Update user's plan and create/update subscription record."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("Webhook: user not found", user_id=user_id)
        return

    # Update user plan
    old_plan = user.plan
    user.plan = plan
    logger.info("Webhook: upgraded user plan",
                user_id=user_id,
                email=user.email,
                old_plan=old_plan,
                new_plan=plan)

    # Upsert subscription record
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    now = datetime.now(timezone.utc)
    days = PLAN_DURATIONS.get(billing_cycle, 30)
    period_end = now + timedelta(days=days)

    if sub:
        sub.plan = plan
        sub.billing_cycle = billing_cycle
        sub.status = "active"
        sub.current_period_start = now
        sub.current_period_end = period_end
        sub.cancel_at_period_end = False
    else:
        sub = Subscription(
            user_id=user_id,
            plan=plan,
            billing_cycle=billing_cycle,
            status="active",
            current_period_start=now,
            current_period_end=period_end,
        )
        db.add(sub)

    db.commit()
    logger.info("Webhook: subscription record updated",
                user_id=user_id,
                plan=plan,
                billing_cycle=billing_cycle,
                period_end=period_end.isoformat())


@router.post("/webhook")
async def dodo_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Dodo Payments webhooks."""
    event = await _parse_webhook_payload(request)
    event_type = event.get("type", "")

    logger.info("Dodo webhook received", event_type=event_type)

    if event_type in ("payment.succeeded", "subscription.created"):
        checkout_id = _extract_checkout_id(event)
        customer_email = _extract_customer_email(event)

        # First try to find by checkout session id
        pending = None
        if checkout_id:
            pending = db.query(PendingPayment).filter(
                PendingPayment.checkout_session_id == checkout_id,
                PendingPayment.status == "pending",
            ).first()

        # Fallback: find most recent pending payment for this customer
        if not pending and customer_email:
            user = db.query(User).filter(User.email == customer_email).first()
            if user:
                pending = db.query(PendingPayment).filter(
                    PendingPayment.user_id == user.id,
                    PendingPayment.status == "pending",
                ).order_by(PendingPayment.created_at.desc()).first()

        if pending:
            _upgrade_user_plan(db, pending.user_id, pending.plan, pending.billing_cycle)
            pending.status = "completed"
            db.commit()
            logger.info("Webhook: payment completed",
                        user_id=pending.user_id,
                        plan=pending.plan,
                        checkout_id=checkout_id)
        else:
            logger.warning("Webhook: no pending payment found",
                           checkout_id=checkout_id,
                           email=customer_email)

    elif event_type == "subscription.cancelled":
        # Mark subscription as cancelled
        checkout_id = _extract_checkout_id(event)
        if checkout_id:
            pending = db.query(PendingPayment).filter(
                PendingPayment.checkout_session_id == checkout_id,
            ).first()
            if pending:
                user = db.query(User).filter(User.id == pending.user_id).first()
                if user:
                    # Revert to free when cancelled (or keep until period_end based on policy)
                    # For now: keep current plan until period_end logic is implemented
                    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
                    if sub:
                        sub.status = "cancelled"
                        sub.cancel_at_period_end = True
                        db.commit()
                        logger.info("Webhook: subscription marked for cancellation",
                                    user_id=user.id)

    return {"status": "success"}


# ---------------------------------------------------------------------------
# Debug helpers (only available when DEBUG=true)
# ---------------------------------------------------------------------------

class SimulateWebhookRequest(BaseModel):
    user_id: int
    plan: str
    billing_cycle: str = "monthly"


@router.post("/simulate-webhook")
def simulate_webhook(
    req: SimulateWebhookRequest,
    db: Session = Depends(get_db),
):
    """Simulate a successful payment webhook (debug only)."""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Debug endpoint only")

    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _upgrade_user_plan(db, req.user_id, req.plan, req.billing_cycle)

    return {
        "message": f"User {user.email} upgraded to {req.plan} ({req.billing_cycle})",
        "user_id": req.user_id,
        "plan": req.plan,
    }


@router.get("/my-subscription")
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription status."""
    sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
    ).first()

    return {
        "plan": current_user.plan,
        "subscription": {
            "plan": sub.plan if sub else current_user.plan,
            "billing_cycle": sub.billing_cycle if sub else None,
            "status": sub.status if sub else "active" if current_user.plan != "free" else None,
            "current_period_start": sub.current_period_start.isoformat() if sub and sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end if sub else False,
        } if sub else None,
    }
