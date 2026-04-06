import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, role: str = "user") -> User:
        user = User(email=email, hashed_password=hashed_password, role=role)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_all(self) -> list[User]:
        result = await self._session.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        await self._session.commit()
        await self._session.refresh(user)
        return user
