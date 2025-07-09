"""
Database connection and session management
SQLAlchemy with async support
"""

import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.models import Base

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.db_echo)
AsyncSessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_database():
    """Veritabanını ve tabloları oluşturur."""
    async with engine.begin() as conn:
        try:
            # await conn.run_sync(Base.metadata.drop_all) # Geliştirme için gerekirse
            await conn.run_sync(Base.metadata.create_all)
            logger.info(f"✅ Async database initialized and tables created: {settings.database_url}")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """Dependency for getting a database session."""
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"DB Session error: {e}")
        raise
    finally:
        await session.close()

@asynccontextmanager
async def get_db() -> AsyncSession:
    """Async context manager for DB session (compatible with 'async with')."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"DB Session error: {e}")
            raise 