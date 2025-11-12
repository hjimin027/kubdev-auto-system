"""
Database Connection and Session Management
SQLAlchemy 데이터베이스 연결 관리
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from .config import settings

# 동기 데이터베이스 엔진
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=300,    # 연결 재사용 시간
)

# 비동기 데이터베이스 엔진
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_recycle=300,
)

# 세션 팩토리
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base 클래스
Base = declarative_base()

# 데이터베이스 의존성
async def get_async_session() -> AsyncSession:
    """비동기 데이터베이스 세션 제공"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_session():
    """동기 데이터베이스 세션 제공"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()