from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.config import get_settings

settings = get_settings()

# Simple in-memory store for email verification codes (replace with Redis in production)
_verification_codes = {}


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


def authenticate_user(db: Session, login_data: UserLogin) -> User | None:
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        return None
    if not user.password_hash:
        return None
    if not verify_password(login_data.password, user.password_hash):
        return None
    return user


def get_or_create_google_user(db: Session, google_id: str, email: str, name: str | None, avatar: str | None) -> User:
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
    _verification_codes[email] = code
    return code


def verify_email_code(email: str, code: str) -> bool:
    stored = _verification_codes.get(email)
    if stored and stored == code:
        del _verification_codes[email]
        return True
    return False


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_token_for_user(user: User) -> str:
    return create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
    })
