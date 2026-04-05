import json
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _json_serializer(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False)


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    json_serializer=_json_serializer,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
