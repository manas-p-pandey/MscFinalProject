from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ML_Data(BaseModel):
    site_code : str
    site_name: str
    site_type: str
    latitude: float
    longitude: float
    datetime: datetime
    aqi: int
    co: float
    no: float
    no2: float
    o3: float
    so2: float
    pm2_5: float
    pm10: float
    nh3: float
    temp: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float
    wind_speed: float
    wind_deg: int
    traffic_flow: str
    traffic_density: str

    class Config:
        orm_mode = True