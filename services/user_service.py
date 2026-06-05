from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Like, PendingLike, Blacklist

DAILY_LIKE_LIMIT = 30
PENDING_EXPIRE_HOURS = 3
AGE_RANGE_BELOW = 3
AGE_RANGE_ABOVE = 4

# Антиспам: не более N лайков в минуту
ANTISPAM_LIKES_PER_MINUTE = 8
# Серия дней: буст анкеты на 24ч при достижении порога
STREAK_MILESTONES = {7: 24, 14: 48}   # streak_days -> boost_hours


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    return await session.get(User, user_id)


async def create_user(session: AsyncSession, **kwargs) -> User:
    user = User(**kwargs)
    session.add(user)
    await session.commit()
    return user


async def update_user(session: AsyncSession, user_id: int, **kwargs) -> None:
    await session.execute(
        update(User).where(User.user_id == user_id).values(**kwargs)
    )
    await session.commit()


async def is_registered(session: AsyncSession, user_id: int) -> bool:
    return await get_user(session, user_id) is not None


def is_lovaplus_active(user: User) -> bool:
    return bool(user.is_lovaplus and user.lovaplus_until and user.lovaplus_until >= date.today())


async def can_like(session: AsyncSession, user: User) -> bool:
    if is_lovaplus_active(user):
        return True
    return user.likes_today < DAILY_LIKE_LIMIT


# ── Антиспам ──────────────────────────────────────────────────────────────────

async def check_antispam(session: AsyncSession, user: User) -> Tuple[bool, str]:
    """
    Returns (allowed, reason).
    Проверяет: не более ANTISPAM_LIKES_PER_MINUTE лайков в минуту.
    """
    now = datetime.utcnow()
    if user.last_like_time and (now - user.last_like_time).total_seconds() < 60:
        count = (user.likes_last_minute or 0) + 1
        if count > ANTISPAM_LIKES_PER_MINUTE:
            return False, (
                f"🚫 Слишком быстро! Подождите немного.\n"
                f"Лимит: {ANTISPAM_LIKES_PER_MINUTE} лайков в минуту."
            )
        new_count = count
    else:
        new_count = 1

    await session.execute(
        update(User)
        .where(User.user_id == user.user_id)
        .values(likes_last_minute=new_count, last_like_time=now)
    )
    await session.commit()
    return True, ""


# ── Серия дней ────────────────────────────────────────────────────────────────

async def record_activity(session: AsyncSession, user_id: int) -> Optional[int]:
    """
    Обновляет серию дней при входе пользователя.
    Returns boost_hours если достигнут milestone, иначе None.
    """
    user = await get_user(session, user_id)
    if not user:
        return None

    today = date.today()
    if user.last_activity_date == today:
        return None  # уже засчитано сегодня

    yesterday = today - timedelta(days=1)
    if user.last_activity_date == yesterday:
        new_streak = (user.activity_streak or 0) + 1
    else:
        new_streak = 1  # серия прервана

    boost_hours = None
    boost_until = user.streak_boost_until

    # Проверяем достижение milestone
    for milestone_days, hours in sorted(STREAK_MILESTONES.items()):
        if new_streak == milestone_days:
            boost_hours = hours
            boost_until = datetime.utcnow() + timedelta(hours=hours)
            break

    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(
            last_activity_date=today,
            activity_streak=new_streak,
            streak_boost_until=boost_until,
        )
    )
    await session.commit()
    return boost_hours


def has_streak_boost(user: User) -> bool:
    return bool(user.streak_boost_until and user.streak_boost_until > datetime.utcnow())


# ── Поиск с фильтрами ────────────────────────────────────────────────────────

async def get_next_profile(
    session: AsyncSession,
    user: User,
    already_seen: List[int],
) -> Optional[User]:
    """
    Находит следующую анкету для показа.
    LovaPlus: использует filter_age_min/max и filter_city если заданы.
    Учитывает чёрный список, антиспам, буст (streak_boost).
    """
    today = date.today()
    lovaplus = is_lovaplus_active(user)

    # Определяем параметры поиска
    if lovaplus and user.filter_age_min is not None:
        age_min = user.filter_age_min
    else:
        age_min = user.age - AGE_RANGE_BELOW

    if lovaplus and user.filter_age_max is not None:
        age_max = user.filter_age_max
    else:
        age_max = user.age + AGE_RANGE_ABOVE

    if lovaplus and user.filter_city:
        city = user.filter_city
    else:
        city = user.city

    excluded = list(set(already_seen + [user.user_id]))

    # Лайкнутые уже
    liked_result = await session.execute(
        select(Like.liked_user_id).where(Like.user_id == user.user_id)
    )
    liked_ids = [r[0] for r in liked_result.fetchall()]
    excluded.extend(liked_ids)

    # Чёрный список (обе стороны)
    bl_result = await session.execute(
        select(Blacklist.blocked_id).where(Blacklist.user_id == user.user_id)
    )
    blocked_by_me = [r[0] for r in bl_result.fetchall()]

    bl_me_result = await session.execute(
        select(Blacklist.user_id).where(Blacklist.blocked_id == user.user_id)
    )
    blocked_me = [r[0] for r in bl_me_result.fetchall()]

    excluded.extend(blocked_by_me)
    excluded.extend(blocked_me)

    # Сортировка: буст (streak) > lovaplus > random
    now = datetime.utcnow()
    result = await session.execute(
        select(User)
        .where(
            and_(
                User.user_id.notin_(excluded),
                User.city == city,
                User.age >= age_min,
                User.age <= age_max,
                User.is_banned == False,
            )
        )
        .order_by(
            # Сначала те, у кого активный буст от серии
            (User.streak_boost_until > now).desc(),
            # Затем LovaPlus
            User.is_lovaplus.desc(),
            func.random(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def increment_likes_today(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(likes_today=User.likes_today + 1)
    )
    await session.commit()


async def increment_profiles_viewed(session: AsyncSession, user_id: int) -> bool:
    user = await get_user(session, user_id)
    if not user:
        return False
    new_count = user.profiles_viewed_since_last_warning + 1
    should_warn = new_count >= 30
    if should_warn:
        new_count = 0
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(profiles_viewed_since_last_warning=new_count)
    )
    await session.commit()
    return should_warn


# ── Фильтры поиска (LovaPlus) ─────────────────────────────────────────────────

async def set_search_filters(
    session: AsyncSession,
    user_id: int,
    age_min: Optional[int],
    age_max: Optional[int],
    city: Optional[str],
) -> None:
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(filter_age_min=age_min, filter_age_max=age_max, filter_city=city)
    )
    await session.commit()


async def reset_search_filters(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(filter_age_min=None, filter_age_max=None, filter_city=None)
    )
    await session.commit()


# ── Чёрный список ─────────────────────────────────────────────────────────────

async def add_to_blacklist(session: AsyncSession, user_id: int, blocked_id: int) -> bool:
    """Returns False если уже есть."""
    existing = await session.get(Blacklist, (user_id, blocked_id))
    if existing:
        return False
    session.add(Blacklist(user_id=user_id, blocked_id=blocked_id))
    await session.commit()
    return True


async def remove_from_blacklist(session: AsyncSession, user_id: int, blocked_id: int) -> bool:
    existing = await session.get(Blacklist, (user_id, blocked_id))
    if not existing:
        return False
    await session.delete(existing)
    await session.commit()
    return True


async def get_blacklist(session: AsyncSession, user_id: int) -> List[Blacklist]:
    result = await session.execute(
        select(Blacklist).where(Blacklist.user_id == user_id)
    )
    return result.scalars().all()


# ── Background task helpers ────────────────────────────────────────────────────

async def reset_daily_likes_all(session: AsyncSession) -> None:
    await session.execute(
        update(User).values(likes_today=0, last_like_reset=date.today())
    )
    await session.commit()


async def expire_lovaplus_all(session: AsyncSession) -> None:
    today = date.today()
    await session.execute(
        update(User)
        .where(and_(User.lovaplus_until != None, User.lovaplus_until < today))
        .values(is_lovaplus=False, lovaplus_until=None)
    )
    await session.commit()


async def add_lovaplus(session: AsyncSession, user_id: int, days: int) -> date:
    user = await get_user(session, user_id)
    if not user:
        raise ValueError("User not found")
    base = user.lovaplus_until if (user.lovaplus_until and user.lovaplus_until >= date.today()) else date.today()
    new_until = base + timedelta(days=days)
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(is_lovaplus=True, lovaplus_until=new_until)
    )
    await session.commit()
    return new_until


async def revoke_lovaplus(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(is_lovaplus=False, lovaplus_until=None)
    )
    await session.commit()


async def get_all_non_lovaplus_users(session: AsyncSession) -> List[User]:
    today = date.today()
    result = await session.execute(
        select(User).where(
            or_(
                User.is_lovaplus == False,
                User.lovaplus_until == None,
                User.lovaplus_until < today,
            )
        )
    )
    return result.scalars().all()
