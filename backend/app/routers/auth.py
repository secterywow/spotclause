from fastapi import APIRouter, Depends, HTTPException, status
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


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    from app.models.user import User
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user(db, user_data)
    token = create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/google", response_model=Token)
def google_login(data: GoogleLogin, db: Session = Depends(get_db)):
    # In production, verify Google ID token with Google API
    # For development, we accept the token as user info
    # TODO: Implement proper Google token verification
    import json
    try:
        payload = json.loads(data.token)
        google_id = payload.get("sub") or payload.get("id")
        email = payload.get("email")
        name = payload.get("name")
        avatar = payload.get("picture")
    except:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Invalid Google token data")

    user = get_or_create_google_user(db, google_id, email, name, avatar)
    token = create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/verify-email/send")
def send_verification_code(email: str):
    code = generate_email_code(email)
    # TODO: Send email with code
    # For development, return the code directly
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
def get_current_user(token: str, db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.models.user import User
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
