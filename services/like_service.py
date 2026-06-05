from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Like, PendingLike, User

PENDING_EXPIRE_HOURS = 3


async def has_liked(session: AsyncSession, from_id: int, to_id: int) -> bool:
    result = await session.execute(
        select(Like).where(
            and_(Like.user_id == from_id, Like.liked_user_id == to_id)
        )
    )
    return result.scalar_one_or_none() is not None


async def get_pending_like(session: AsyncSession, from_id: int, to_id: int) -> Optional[PendingLike]:
    result = await session.execute(
        select(PendingLike).where(
            and_(PendingLike.user_id == from_id, PendingLike.target_id == to_id)
        )
    )
    return result.scalar_one_or_none()


async def record_like(
    session: AsyncSession,
    from_id: int,
    to_id: int,
    is_lovaplus_like: bool,
) -> Tuple[bool, bool]:
    """
    Records a like from from_id → to_id.
    Returns (is_match, already_liked).
    """
    # Check already liked
    if await has_liked(session, from_id, to_id):
        return False, True

    # Save to likes table
    like = Like(user_id=from_id, liked_user_id=to_id)
    session.add(like)

    # Check mutual
    is_match = await has_liked(session, to_id, from_id)

    if is_match:
        # Delete pending likes in both directions
        await session.execute(
            delete(PendingLike).where(
                and_(PendingLike.user_id == from_id, PendingLike.target_id == to_id)
            )
        )
        await session.execute(
            delete(PendingLike).where(
                and_(PendingLike.user_id == to_id, PendingLike.target_id == from_id)
            )
        )
    else:
        # Remove old pending if exists, add fresh
        await session.execute(
            delete(PendingLike).where(
                and_(PendingLike.user_id == from_id, PendingLike.target_id == to_id)
            )
        )
        pending = PendingLike(
            user_id=from_id,
            target_id=to_id,
            is_lovaplus_like=is_lovaplus_like,
        )
        session.add(pending)

    await session.commit()
    return is_match, False


async def get_pending_likes_for_user(
    session: AsyncSession,
    target_id: int,
) -> List[Tuple[PendingLike, bool]]:
    """Returns list of (pending_like, is_expired)."""
    now = datetime.utcnow()
    expire_cutoff = now - timedelta(hours=PENDING_EXPIRE_HOURS)

    result = await session.execute(
        select(PendingLike).where(PendingLike.target_id == target_id)
    )
    pending_likes = result.scalars().all()

    output = []
    for pl in pending_likes:
        expired = (not pl.is_lovaplus_like) and (pl.created_at < expire_cutoff)
        output.append((pl, expired))

    return output


async def delete_pending_like(session: AsyncSession, from_id: int, to_id: int) -> None:
    await session.execute(
        delete(PendingLike).where(
            and_(PendingLike.user_id == from_id, PendingLike.target_id == to_id)
        )
    )
    await session.commit()


async def cleanup_expired_pending(session: AsyncSession) -> int:
    """Delete non-lovaplus pending likes older than 3 hours. Returns count deleted."""
    expire_cutoff = datetime.utcnow() - timedelta(hours=PENDING_EXPIRE_HOURS)
    result = await session.execute(
        delete(PendingLike).where(
            and_(
                PendingLike.is_lovaplus_like == False,
                PendingLike.created_at < expire_cutoff,
            )
        )
    )
    await session.commit()
    return result.rowcount
