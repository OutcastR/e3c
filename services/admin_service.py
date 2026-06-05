from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin, Like, Report, User


async def get_admin_level(session: AsyncSession, user_id: int, config_admins: Dict[int, int]) -> Optional[int]:
    """Returns admin level or None. Checks both config and DB."""
    if user_id in config_admins:
        return config_admins[user_id]
    result = await session.get(Admin, user_id)
    return result.level if result else None


async def add_admin(session: AsyncSession, user_id: int, level: int) -> None:
    existing = await session.get(Admin, user_id)
    if existing:
        existing.level = level
    else:
        session.add(Admin(user_id=user_id, level=level))
    await session.commit()


async def remove_admin(session: AsyncSession, user_id: int) -> bool:
    admin = await session.get(Admin, user_id)
    if admin:
        await session.delete(admin)
        await session.commit()
        return True
    return False


async def get_all_admins(session: AsyncSession) -> List[Admin]:
    result = await session.execute(select(Admin))
    return result.scalars().all()


async def get_stats(session: AsyncSession) -> Dict:
    today = date.today()

    total_users = (await session.execute(func.count(User.user_id).select())).scalar() or 0
    active_subs = (
        await session.execute(
            func.count(User.user_id).select().where(
                and_(User.is_lovaplus == True, User.lovaplus_until >= today)
            )
        )
    ).scalar() or 0

    # Matches today = likes created today where mutual
    today_dt = datetime.combine(today, datetime.min.time())
    likes_today_result = await session.execute(
        select(Like).where(Like.created_at >= today_dt)
    )
    likes_today = likes_today_result.scalars().all()
    liked_pairs = {(l.user_id, l.liked_user_id) for l in likes_today}
    matches_today = sum(
        1 for (a, b) in liked_pairs if (b, a) in liked_pairs
    ) // 2

    open_reports = (
        await session.execute(
            func.count(Report.id).select().where(Report.resolved == False)
        )
    ).scalar() or 0

    return {
        "total_users": total_users,
        "active_subs": active_subs,
        "matches_today": matches_today,
        "open_reports": open_reports,
    }


def get_log_tail(n: int = 50) -> str:
    try:
        with open("logs/bot.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
        tail = lines[-n:] if len(lines) >= n else lines
        return "".join(tail)
    except FileNotFoundError:
        return "Лог-файл не найден."
