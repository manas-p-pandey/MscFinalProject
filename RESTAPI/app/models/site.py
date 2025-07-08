from sqlalchemy import Column, String, Float, DateTime
from app.core.database import Base

class Site(Base):
    __tablename__ = "site_table"

    site_code = Column(String, primary_key=True, index=True)
    site_name = Column(String)
    site_type = Column(String)
    local_authority_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    latitudewgs84 = Column(Float)
    longitudewgs84 = Column(Float)
    date_opened = Column(DateTime)
    date_closed = Column(DateTime)
    site_link = Column(String)
