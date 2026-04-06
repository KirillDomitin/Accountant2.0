"""APScheduler — ежедневная проверка отслеживаемых ИНН."""
import logging

import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _daily_check_job() -> None:
    from app.services.tracking_service import check_all_tracked_inns

    logger.info("Scheduler: daily_inn_check job triggered")
    async with async_session_factory() as session:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await check_all_tracked_inns(session, redis)
        except Exception as exc:
            logger.error("Scheduler: daily_inn_check job failed: %s", exc, exc_info=True)
        finally:
            await redis.aclose()


def setup_scheduler() -> None:
    scheduler.add_job(
        _daily_check_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="daily_inn_check",
        replace_existing=True,
    )
