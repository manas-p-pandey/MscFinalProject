from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.historical_data_view import historical_data_view
from datetime import datetime

async def historical_service(db: AsyncSession, parsed_dt: datetime):
    # Use direct filter on datetime field
    stmt = select(historical_data_view).where(historical_data_view.datetime == parsed_dt)
    result = await db.execute(stmt)
    return result.scalars().all()
