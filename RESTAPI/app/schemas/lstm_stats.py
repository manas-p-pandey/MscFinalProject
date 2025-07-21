from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime

# Output model (what client receives)
class lstm_stats(BaseModel):
    created_at:datetime
    model_name:str
    test_accuracy:float
    test_loss:float

    @field_serializer("test_accuracy", "test_loss")
    def round_floats(self, v: float) -> float:
        return round(v, 4)

    class Config:
        orm_mode = True
