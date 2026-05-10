from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from app.database import Base


class ContractRecord(Base):
    __tablename__ = "contract_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20))
    contract_type = Column(String(50))
    jurisdiction = Column(String(50))
    overall_score = Column(Integer)
    high_risk_count = Column(Integer, default=0)
    medium_risk_count = Column(Integer, default=0)
    low_risk_count = Column(Integer, default=0)
    report_json = Column(Text)  # 完整报告(JSON)
    messages_json = Column(Text)  # 追问对话(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="contracts")
    messages = relationship("ContractMessage", back_populates="contract", cascade="all, delete-orphan")


class ContractMessage(Base):
    __tablename__ = "contract_messages"
    __table_args__ = (Index("ix_contract_messages_contract_round", "contract_record_id", "round"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contract_record_id = Column(BigInteger, ForeignKey("contract_records.id", ondelete="CASCADE"), nullable=False)
    round = Column(Integer, nullable=False)
    role = Column(Enum("user", "assistant", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("ContractRecord", back_populates="messages")
