from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, UniqueConstraint, func
from app.database import Base


class UsageTracking(Base):
    __tablename__ = "usage_tracking"
    __table_args__ = (UniqueConstraint("user_id", "month", name="uix_usage_user_month"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    month = Column(String(7), nullable=False)  # "2026-05"
    analyze_count = Column(Integer, default=0)
    compare_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
