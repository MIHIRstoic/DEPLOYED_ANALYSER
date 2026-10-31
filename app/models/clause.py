from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(
        Integer,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    clause_number = Column(String, nullable=True)
    clause_type = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)

    contract = relationship("Contract", back_populates="clauses")
    risks = relationship(
        "Risk",
        back_populates="clause",
        cascade="all, delete-orphan",
    )
