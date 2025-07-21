from pydantic import BaseModel
from typing import List
from app.schemas.lstm_stats import lstm_stats
from app.schemas.regressor_stats import regressor_stats

class DashboardResponse(BaseModel):
    lstm_stats: List[lstm_stats]
    regressor_stats: List[regressor_stats]