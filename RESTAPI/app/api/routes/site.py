from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from typing import List

from app.schemas.site import SiteDetails
from app.services.site_service import get_all_sites

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=List[SiteDetails])
async def read_sites(db: AsyncSession = Depends(get_db)):
    sites = await get_all_sites(db)
    return sites
