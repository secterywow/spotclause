from sqlalchemy import Column, BigInteger, String, Text, Enum, JSON, Boolean, DateTime, Index, func
from app.database import Base


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(String(50), unique=True, nullable=False)
    contract_types = Column(JSON, nullable=False)  # ["nda", "service"]
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    standard_practice = Column(Text)
    suggested_alternative = Column(Text)
    legal_basis = Column(String(500))
    severity = Column(Enum("high", "medium", "low", name="rule_severity"), nullable=False)
    keywords = Column(JSON)  # ["预付", "预付款"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_risk_rules_contract_types", "contract_types"),
        Index("ix_risk_rules_category", "category"),
        Index("ix_risk_rules_severity", "severity"),
    )
