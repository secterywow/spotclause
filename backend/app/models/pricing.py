from sqlalchemy import Column, BigInteger, String, Numeric, JSON, Boolean, DateTime, func
from app.database import Base


class RegionalPricing(Base):
    __tablename__ = "regional_pricing"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    country_code = Column(String(2), unique=True, nullable=False, index=True)  # "US", "CN"
    region_name = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    free_plan = Column(JSON, default={})  # 免费套餐配置
    standard_monthly = Column(Numeric(10, 2), nullable=False)
    standard_yearly = Column(Numeric(10, 2), nullable=False)
    pro_monthly = Column(Numeric(10, 2), nullable=False)
    pro_yearly = Column(Numeric(10, 2), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
