from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.dashboard_response import DashboardResponse
from app.services.dashboard_service import all_lstm_stats, all_regressor_stats
from app.core.database import SessionLocal

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=DashboardResponse)
async def read_dashboard_records(
    db: AsyncSession = Depends(get_db)
):
    try:
        lstm_data = await all_lstm_stats(db)
        regressor_data = await all_regressor_stats(db)

        return {
            "lstm_stats": lstm_data,
            "regressor_stats": regressor_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
