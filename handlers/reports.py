from aiogram import F, Router
from aiogram.types import CallbackQuery

from database import async_session_maker
from keyboards.keyboards import main_menu_kb, report_reasons_kb, REPORT_REASONS
from services.report_service import create_report
from utils.logger import logger

router = Router()


@router.callback_query(F.data.startswith("report_") & ~F.data.startswith("report_reason_"))
async def start_report(callback: CallbackQuery):
    parts = callback.data.split("_")
    target_id = int(parts[1])
    await callback.answer()
    await callback.message.answer(
        "🚨 <b>Пожаловаться на анкету</b>\n\nВыберите причину жалобы:",
        parse_mode="HTML",
        reply_markup=report_reasons_kb(target_id),
    )


@router.callback_query(F.data.startswith("report_reason_"))
async def submit_report(callback: CallbackQuery):
    parts = callback.data.split("_", 3)
    target_id = int(parts[2])
    reason_short = parts[3]

    reason = next((r for r in REPORT_REASONS if r[:20] == reason_short), reason_short)

    async with async_session_maker() as session:
        await create_report(session, callback.from_user.id, target_id, reason)

    logger.info(f"Report: {callback.from_user.id} → {target_id}, reason: {reason}")
    await callback.answer("✅ Жалоба отправлена. Модераторы рассмотрят её.", show_alert=True)
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "cancel_report")
async def cancel_report(callback: CallbackQuery):
    await callback.answer("Отменено.")
    try:
        await callback.message.delete()
    except Exception:
        pass
