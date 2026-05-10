from sqlalchemy import Column, BigInteger, String, Enum, DateTime, Boolean, ForeignKey, func
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    stripe_subscription_id = Column(String(100))
    plan = Column(Enum("standard", "pro", name="subscription_plan"), nullable=False)
    billing_cycle = Column(Enum("monthly", "yearly", name="billing_cycle"), nullable=False)
    status = Column(Enum("active", "cancelled", "past_due", name="subscription_status"), default="active")
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
