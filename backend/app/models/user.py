from sqlalchemy import Column, BigInteger, String, Boolean, Enum, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100))
    avatar = Column(String(500))
    auth_provider = Column(Enum("google", "email", name="auth_provider"), nullable=False)
    google_id = Column(String(100), unique=True)
    password_hash = Column(String(255))
    email_verified = Column(Boolean, default=False)
    role = Column(Enum("user", "admin", name="user_role"), default="user")
    plan = Column(Enum("free", "standard", "pro", name="user_plan"), default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    contracts = relationship("ContractRecord", back_populates="user", cascade="all, delete-orphan")
