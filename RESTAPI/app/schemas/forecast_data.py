from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class TrafficData(BaseModel):
    latitude: float
    longitude: float
    traffic_density: str

class ForecastRequest(BaseModel):
    datetime: datetime
    traffic_data: List[TrafficData]

class ForecastResponse(BaseModel):
    site_code: str
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
    clouds: int
    wind_speed: float
    wind_deg: int
    weather_main: str
    weather_description: str
    traffic_flow: str
    traffic_density: str