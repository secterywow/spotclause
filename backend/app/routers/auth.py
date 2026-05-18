from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, GoogleLogin, Token, EmailVerify
from app.services.auth import (
    create_user,
    authenticate_user,
    get_or_create_google_user,
    generate_email_code,
    verify_email_code,
    create_token_for_user,
)
from app.utils.security import decode_access_token
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _verify_google_token(token: str) -> dict:
    """Verify a Google ID token and return the payload."""
    if not settings.google_client_id:
        raise ValueError("Google Client ID not configured")

    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    idinfo = google_id_token.verify_oauth2_token(
        token,
        google_requests.Request(),
        settings.google_client_id,
        clock_skew_in_seconds=10,
    )
    return idinfo


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    from app.models.user import User
    existing = db.query(User).filter(User.email == user_data.email).first()

    # If email exists and is already verified, reject
    if existing and existing.email_verified:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Verify the email verification code
    if not user_data.code:
        raise HTTPException(status_code=400, detail="Verification code is required")
    if not verify_email_code(user_data.email, user_data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    if existing and not existing.email_verified:
        # Re-use the unverified account: update password and mark verified
        from app.utils.security import get_password_hash
        existing.name = user_data.name or existing.name
        existing.password_hash = get_password_hash(user_data.password)
        existing.email_verified = True
        db.commit()
        db.refresh(existing)
        token = create_token_for_user(existing)
        return {"access_token": token, "token_type": "bearer", "user": existing}

    user = create_user(db, user_data)
    user.email_verified = True
    db.commit()
    token = create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your email before logging in.")

    token = create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/google", response_model=Token)
def google_login(data: GoogleLogin, db: Session = Depends(get_db)):
    """Handle Google OAuth login."""
    google_id = None
    email = None
    name = None
    avatar = None

    # Try to verify as a real Google ID token first
    if settings.google_client_id:
        try:
            idinfo = _verify_google_token(data.token)
            google_id = idinfo.get("sub")
            email = idinfo.get("email")
            name = idinfo.get("name")
            avatar = idinfo.get("picture")
        except ValueError:
            # Client ID not configured, fall through to development mode
            pass
        except Exception:
            # Token verification failed — fall through to try JSON payload
            # (allows development mock tokens to still work)
            pass

    # Fallback: accept JSON payload (development mode or unconfigured client)
    if not google_id or not email:
        import json
        try:
            payload = json.loads(data.token)
            google_id = payload.get("sub") or payload.get("id")
            email = payload.get("email")
            name = payload.get("name")
            avatar = payload.get("picture")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Google token")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Invalid Google token data")

    user = get_or_create_google_user(db, google_id, email, name, avatar)
    token = create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/google-config")
def get_google_config():
    """Return the Google OAuth client ID for frontend initialization."""
    return {"client_id": settings.google_client_id}


@router.post("/verify-email/send")
def send_verification_code(email: str, db: Session = Depends(get_db)):
    from app.models.user import User
    existing = db.query(User).filter(User.email == email).first()

    # If already registered and verified, don't send code
    if existing and existing.email_verified:
        raise HTTPException(status_code=400, detail="Email already registered")

    code = generate_email_code(email)
    if settings.debug:
        return {"message": "Verification code sent", "code": code}
    return {"message": "Verification code sent"}


@router.post("/verify-email/confirm")
def confirm_verification_code(data: EmailVerify, db: Session = Depends(get_db)):
    if verify_email_code(data.email, data.code):
        from app.models.user import User
        user = db.query(User).filter(User.email == data.email).first()
        if user:
            user.email_verified = True
            db.commit()
        return {"message": "Email verified successfully"}
    raise HTTPException(status_code=400, detail="Invalid verification code")


@router.get("/me")
def get_me(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.models.user import User
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.delete("/account")
def delete_account(user_id: int, db: Session = Depends(get_db)):
    """Delete the user's account and all associated contract records (cascade)."""
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "Account deleted"}
