from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, VerificationRequest


async def create_verification_request(
    session: AsyncSession,
    user_id: int,
    video_id: str,
) -> VerificationRequest:
    """Создаёт заявку на видеоверификацию."""
    # Удаляем старые pending заявки
    await session.execute(
        session.query(VerificationRequest)
        .filter(
            VerificationRequest.user_id == user_id,
            VerificationRequest.status == 'pending'
        )
        .delete()
    )

    req = VerificationRequest(user_id=user_id, video_id=video_id, status='pending')
    session.add(req)
    await session.commit()
    return req


async def get_pending_verifications(session: AsyncSession) -> List[VerificationRequest]:
    """Получить все pending заявки на верификацию."""
    result = await session.execute(
        select(VerificationRequest)
        .where(VerificationRequest.status == 'pending')
        .order_by(VerificationRequest.created_at)
    )
    return result.scalars().all()


async def approve_verification(session: AsyncSession, req_id: int) -> None:
    """Одобрить верификацию."""
    req = await session.get(VerificationRequest, req_id)
    if not req:
        return

    user_id = req.user_id
    req.status = 'approved'

    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(is_verified=True, video_id=req.video_id)
    )
    await session.commit()


async def reject_verification(session: AsyncSession, req_id: int) -> None:
    """Отклонить верификацию."""
    req = await session.get(VerificationRequest, req_id)
    if not req:
        return
    req.status = 'rejected'
    await session.commit()


async def is_verified(user: User) -> bool:
    return bool(user.is_verified)
