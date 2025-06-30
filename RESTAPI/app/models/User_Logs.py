from sqlalchemy import Column, BigInteger, String, Boolean, Text, ForeignKey, ARRAY
from app.core.database import Base

class User_Logs(Base):
    __tablename__ = 'User_Logs'
    __table_args__ = {'schema': 'public'}

    ID = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    User_ID = Column(BigInteger, ForeignKey("public.User_Details.ID"), nullable=False)
    Module = Column(Text, nullable=False)
    Action = Column(Text)
    Result = Column(Text)
    Details = Column(Text)
