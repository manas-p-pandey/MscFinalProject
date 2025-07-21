from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.synthetic_lstm_stats import synthetic_lstm_stats
from app.models.regressor_stats import regressor_stats
from datetime import datetime

async def all_lstm_stats(db: AsyncSession):
    # Use direct filter on datetime field
    stmt = select(synthetic_lstm_stats)
    result = await db.execute(stmt)
    return result.scalars().all()

async def all_regressor_stats(db: AsyncSession):
    # Use direct filter on datetime field
    stmt = select(regressor_stats)
    result = await db.execute(stmt)
    return result.scalars().all()