from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Promocode, PromocodeUsage
from services.user_service import add_lovaplus


async def create_promocode(
    session: AsyncSession,
    code: str,
    days: int,
    max_uses: int,
    created_by: int,
) -> Promocode:
    promo = Promocode(code=code, days=days, max_uses=max_uses, created_by=created_by)
    session.add(promo)
    await session.commit()
    return promo


async def get_promocode(session: AsyncSession, code: str) -> Optional[Promocode]:
    result = await session.execute(
        select(Promocode).where(Promocode.code == code)
    )
    return result.scalar_one_or_none()


async def has_used_promocode(session: AsyncSession, promo_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(PromocodeUsage).where(
            and_(
                PromocodeUsage.promocode_id == promo_id,
                PromocodeUsage.user_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def apply_promocode(
    session: AsyncSession,
    code: str,
    user_id: int,
) -> tuple[bool, str]:
    """Returns (success, message)."""
    promo = await get_promocode(session, code)
    if not promo:
        return False, "❌ Промокод не найден."
    if not promo.is_active:
        return False, "❌ Промокод недействителен."
    if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
        return False, "❌ Промокод исчерпал лимит использований."
    if await has_used_promocode(session, promo.id, user_id):
        return False, "❌ Вы уже использовали этот промокод."

    # Apply
    new_until = await add_lovaplus(session, user_id, promo.days)

    # Record usage
    usage = PromocodeUsage(promocode_id=promo.id, user_id=user_id)
    session.add(usage)
    promo.used_count += 1
    await session.commit()

    return True, (
        f"✅ Промокод активирован! LovaPlus добавлен на {promo.days} дней.\n"
        f"Подписка действует до: {new_until.strftime('%d %B %Y г.')}"
    )
