from sqlalchemy import Column, Text, DateTime, Float
from app.core.database import Base

class regressor_stats(Base):
    __tablename__ = 'regressor_stats'

    created_at = Column(DateTime, primary_key=True, index=True)
    model = Column(Text, nullable=False)
    rmse = Column(Float, nullable=False)
    mae = Column(Float, nullable=False)
    r2 = Column(Float, nullable=False)
