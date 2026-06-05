import asyncio
from datetime import datetime, time

from database import async_session_maker
from services.like_service import cleanup_expired_pending
from services.user_service import expire_lovaplus_all, reset_daily_likes_all
from utils.logger import logger


async def task_cleanup_expired_pending():
    """Every 30 minutes: delete non-lovaplus pending likes older than 3h."""
    while True:
        try:
            async with async_session_maker() as session:
                count = await cleanup_expired_pending(session)
            if count:
                logger.info(f"[cleanup_expired_pending] Removed {count} expired pending likes.")
        except Exception as e:
            logger.error(f"[cleanup_expired_pending] Error: {e}")
        await asyncio.sleep(30 * 60)


async def task_reset_daily_likes():
    """Every day at 00:00 UTC: reset likes_today for all users."""
    while True:
        now = datetime.utcnow()
        next_midnight = datetime.combine(now.date(), time(0, 0, 0))
        if next_midnight <= now:
            from datetime import timedelta
            next_midnight = next_midnight + timedelta(days=1)
        wait_seconds = (next_midnight - now).total_seconds()
        logger.info(f"[reset_daily_likes] Next reset in {wait_seconds:.0f}s")
        await asyncio.sleep(wait_seconds)
        try:
            async with async_session_maker() as session:
                await reset_daily_likes_all(session)
            logger.info("[reset_daily_likes] Daily likes reset done.")
        except Exception as e:
            logger.error(f"[reset_daily_likes] Error: {e}")


async def task_check_expired_lovaplus():
    """Every day at 00:00 UTC: expire lovaplus for users past their date."""
    while True:
        now = datetime.utcnow()
        next_midnight = datetime.combine(now.date(), time(0, 5, 0))  # 00:05 UTC
        if next_midnight <= now:
            from datetime import timedelta
            next_midnight = next_midnight + timedelta(days=1)
        wait_seconds = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            async with async_session_maker() as session:
                await expire_lovaplus_all(session)
            logger.info("[check_expired_lovaplus] LovaPlus expiry check done.")
        except Exception as e:
            logger.error(f"[check_expired_lovaplus] Error: {e}")


def start_background_tasks() -> list:
    tasks = [
        asyncio.create_task(task_cleanup_expired_pending()),
        asyncio.create_task(task_reset_daily_likes()),
        asyncio.create_task(task_check_expired_lovaplus()),
    ]
    logger.info("Background tasks started.")
    return tasks
