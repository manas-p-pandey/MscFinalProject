from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SiteDetails(BaseModel):
    site_code: str
    site_name: Optional[str]
    site_type: Optional[str]
    local_authority_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    latitudewgs84: Optional[float]
    longitudewgs84: Optional[float]
    date_opened: Optional[datetime]
    date_closed: Optional[datetime]
    site_link: Optional[str]

    class Config:
        orm_mode = True
