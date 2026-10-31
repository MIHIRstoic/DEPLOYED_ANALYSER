from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Risk(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clause_id = Column(
        Integer,
        ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_type = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    clause = relationship("Clause", back_populates="risks")
