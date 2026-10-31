from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    contract_type = Column(String, nullable=True)
    upload_date = Column(DateTime, nullable=False, default=utcnow)
    status = Column(String, nullable=False, default="uploaded")
    overall_score = Column(Float, nullable=True)

    clauses = relationship(
        "Clause",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
