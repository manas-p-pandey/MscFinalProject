from sqlalchemy import Column, Text, Float, DateTime
from app.core.database import Base

class synthetic_lstm_stats(Base):
    __tablename__ = "synthetic_lstm_stats"

    created_at = Column(DateTime, primary_key=True, index=True)
    model_name = Column(Text, nullable=False)
    test_accuracy = Column(Float, nullable=False)
    test_loss = Column(Float, nullable=False)
