from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings  # Make sure this has DATABASE_URL

# Async SQLAlchemy engine
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

# Async session maker
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Sync engine (for startup table creation only)
from sqlalchemy import create_engine
sync_engine = create_engine(
    settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
    echo=True
)