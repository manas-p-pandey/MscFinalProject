from sqlalchemy import Column, String, Float, DateTime, Integer
from app.core.database import Base

class ml_data_view(Base):
    __tablename__ = "ml_data_view"

    site_code = Column(String, primary_key=True, index=True)
    site_name = Column(String)
    site_type = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    datetime = Column(DateTime)
    aqi = Column(Integer)
    co = Column(Float)
    no = Column(Float)
    no2 = Column(Float)
    o3 = Column(Float)
    so2 = Column(Float)
    pm2_5 = Column(Float)
    pm10 = Column(Float)
    nh3 = Column(Float)
    temp = Column(Float)
    feels_like = Column(Float)
    pressure = Column(Integer)
    humidity = Column(Integer)
    dew_point = Column(Float)
    wind_speed = Column(Float)
    wind_deg = Column(Integer)
    traffic_flow = Column(String)
    traffic_density = Column(String)
