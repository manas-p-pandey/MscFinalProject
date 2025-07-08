from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.site import Site

async def get_all_sites(db: AsyncSession):
    result = await db.execute(select(Site))
    return result.scalars().all()
