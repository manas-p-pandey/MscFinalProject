from sqlalchemy.ext.asyncio import AsyncSession
from app.models.User_Logs import User_Logs
from app.schemas.User_Logs import UserLogEntry

async def create_user_logs(db: AsyncSession, log: UserLogEntry):
    new_log = User_Logs(**log.dict())
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    return new_log
