from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Report, User

AUTOBАН_THRESHOLD = 5  # 5+ жалоб за 24 часа -> автобан


async def create_report(
    session: AsyncSession,
    reporter_id: int,
    reported_id: int,
    reason: str,
) -> Report:
    report = Report(reporter_id=reporter_id, reported_id=reported_id, reason=reason)
    session.add(report)
    await session.commit()

    # Проверяем автобан
    await check_autobан(session, reported_id)

    return report


async def get_open_reports(session: AsyncSession) -> List[Report]:
    result = await session.execute(
        select(Report).where(Report.resolved == False).order_by(Report.created_at)
    )
    return result.scalars().all()


async def resolve_report(session: AsyncSession, report_id: int) -> None:
    await session.execute(
        update(Report).where(Report.id == report_id).values(resolved=True)
    )
    await session.commit()


async def check_autobан(session: AsyncSession, user_id: int) -> bool:
    """
    Проверяет: 5+ жалоб за последние 24 часа -> автобан.
    Returns True если пользователь заблокирован.
    """
    cutoff = datetime.utcnow() - timedelta(hours=24)
    result = await session.execute(
        select(Report).where(
            and_(
                Report.reported_id == user_id,
                Report.created_at >= cutoff,
                Report.resolved == False,
            )
        )
    )
    reports = result.scalars().all()

    if len(reports) >= AUTOBАН_THRESHOLD:
        await session.execute(
            update(User).where(User.user_id == user_id).values(is_banned=True)
        )
        await session.commit()
        return True

    return False


async def count_reports_24h(session: AsyncSession, user_id: int) -> int:
    """Подсчёт жалоб за последние 24 часа."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    result = await session.execute(
        select(Report).where(
            and_(
                Report.reported_id == user_id,
                Report.created_at >= cutoff,
            )
        )
    )
    return len(result.scalars().all())
