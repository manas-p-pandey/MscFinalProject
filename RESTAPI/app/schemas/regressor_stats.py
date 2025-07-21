from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime

class regressor_stats(BaseModel):
    created_at:datetime
    model:str
    rmse:float
    mae:float
    r2:float

    @field_serializer("rmse", "mae", "r2")
    def round_floats(self, v: float) -> float:
        return round(v, 4)


    class Config:
        orm_mode = True
