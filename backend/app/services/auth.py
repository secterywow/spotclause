import time
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Simple in-memory store for email verification codes (replace with Redis in production)
# Format: {email: {"code": str, "expires_at": float}}
_verification_codes = {}

CODE_TTL_SECONDS = 600  # 10 minutes


def create_user(db: Session, user_data: UserCreate) -> User:
    db_user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=get_password_hash(user_data.password),
        auth_provider="email",
        email_verified=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        return None
    if not user.password_hash:
        return None
    if not verify_password(login_data.password, user.password_hash):
        return None
    return user


def _send_email_via_resend(to: str, subject: str, html_body: str) -> bool:
    """Send email via Resend. Returns True on success."""
    if not settings.resend_api_key:
        logger.warning("Resend API key not configured, skipping email send")
        return False

    try:
        import resend
        resend.api_key = settings.resend_api_key
        from_email = settings.resend_from_email or "onboarding@resend.dev"
        resend.Emails.send({
            "from": from_email,
            "to": to,
            "subject": subject,
            "html": html_body,
        })
        return True
    except Exception as e:
        logger.error("Failed to send email", error=str(e), email=to)
        return False


def get_or_create_google_user(db: Session, google_id: str, email: str, name: Optional[str], avatar: Optional[str]) -> User:
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        return user

    # Check if email already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.google_id = google_id
        db.commit()
        db.refresh(existing)
        return existing

    db_user = User(
        email=email,
        name=name,
        avatar=avatar,
        google_id=google_id,
        auth_provider="google",
        email_verified=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def generate_email_code(email: str) -> str:
    import random
    code = f"{random.randint(100000, 999999)}"
    _verification_codes[email] = {"code": code, "expires_at": time.time() + CODE_TTL_SECONDS}

    # Send the code via email
    subject = f"Your {settings.app_name} verification code"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <h2 style="color: #111; margin-bottom: 8px;">Verify your email</h2>
      <p style="color: #555; font-size: 15px; line-height: 1.5;">
        Use the code below to complete your registration. It expires in 10 minutes.
      </p>
      <div style="background: #f5f5f5; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0;">
        <span style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #111;">{code}</span>
      </div>
      <p style="color: #999; font-size: 13px;">
        If you didn't request this, you can safely ignore this email.
      </p>
      <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
      <p style="color: #999; font-size: 12px;">
        Can't find this email? Please check your spam/junk folder.
      </p>
    </div>
    """
    sent = _send_email_via_resend(email, subject, html)
    if not sent and settings.debug:
        logger.info("Email not sent (no Resend key). Code for debugging", email=email, code=code)

    return code


def verify_email_code(email: str, code: str) -> bool:
    record = _verification_codes.get(email)
    if not record:
        return False
    if time.time() > record["expires_at"]:
        del _verification_codes[email]
        return False
    if record["code"] == code:
        del _verification_codes[email]
        return True
    return False


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_token_for_user(user: User) -> str:
    return create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
    })
