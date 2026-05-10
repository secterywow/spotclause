from sqlalchemy import Column, BigInteger, String, Text, Integer, Numeric, DateTime, func
from app.database import Base


class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    contract_record_id = Column(BigInteger)
    task_type = Column(String(50), nullable=False)  # "analyze", "compare", "follow_up"
    model = Column(String(100))
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 6), default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(20), default="success")  # success, error
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
