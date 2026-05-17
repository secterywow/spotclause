from sqlalchemy import Column, BigInteger, String, Enum, DateTime, ForeignKey, func
from app.database import Base


class PendingPayment(Base):
    """Tracks a checkout session from creation to webhook completion."""
    __tablename__ = "pending_payments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan = Column(Enum("standard", "pro", name="pending_plan"), nullable=False)
    billing_cycle = Column(Enum("monthly", "yearly", name="pending_cycle"), nullable=False)
    checkout_session_id = Column(String(255), unique=True, index=True)
    status = Column(Enum("pending", "completed", "failed", name="pending_status"), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
