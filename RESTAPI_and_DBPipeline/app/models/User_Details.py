from sqlalchemy import Column, BigInteger, String, Boolean, Text, ForeignKey, ARRAY
from app.core.database import Base

class User_Details(Base):
    __tablename__ = "User_Details"
    __table_args__ = {"schema": "public"}

    ID = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    FullName = Column(Text, nullable=False)
    Email = Column(Text, nullable=False, unique=True)
    Organization = Column(Text)
    City = Column(Text, nullable=False)
    Country = Column(Text, nullable=False)
    PurposeOfUse = Column(Text, nullable=False)
    Approved = Column(Boolean, default=False, nullable=False)
    Password = Column(Text)  # Optional: Encrypt this later
