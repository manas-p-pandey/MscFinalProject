from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.forecast_data_view import forecast_data_view
from datetime import datetime

async def forecast_service(db: AsyncSession, parsed_dt: datetime):
    # Use direct filter on datetime field
    stmt = select(forecast_data_view).where(forecast_data_view.datetime == parsed_dt)
    result = await db.execute(stmt)
    return result.scalars().all()
