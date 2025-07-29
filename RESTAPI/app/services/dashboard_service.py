from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.synthetic_lstm_stats import synthetic_lstm_stats
from app.models.regressor_stats import regressor_stats
from datetime import datetime, timedelta

async def all_lstm_stats(db: AsyncSession):
    ten_days_ago = datetime.utcnow() - timedelta(days=10)
    stmt = select(synthetic_lstm_stats).where(synthetic_lstm_stats.created_at >= ten_days_ago)
    result = await db.execute(stmt)
    return result.scalars().all()

async def all_regressor_stats(db: AsyncSession):
    ten_days_ago = datetime.utcnow() - timedelta(days=10)
    stmt = select(regressor_stats).where(regressor_stats.created_at >= ten_days_ago)
    result = await db.execute(stmt)
    return result.scalars().all()