import asyncio
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import async_session_maker
from keyboards.keyboards import (
    admin_manage_admins_kb, admin_menu_kb, admin_report_actions_kb,
    back_to_admin_kb, broadcast_photo_kb, cancel_kb, admin_verification_kb,
)
from services.admin_service import (
    add_admin, get_admin_level, get_all_admins, get_log_tail, get_stats, remove_admin,
)
from services.report_service import get_open_reports, resolve_report, count_reports_24h
from services.user_service import add_lovaplus, get_all_non_lovaplus_users, get_user, revoke_lovaplus, update_user
from services.verification_service import get_pending_verifications, approve_verification, reject_verification
from states.states import AdminStates
from utils.config import load_config
from utils.logger import logger

router = Router()


async def _get_level(user_id: int) -> int | None:
    cfg = load_config()
    async with async_session_maker() as session:
        return await get_admin_level(session, user_id, cfg.admins)


# ── /admin command ─────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_command(message: Message):
    level = await _get_level(message.from_user.id)
    if not level:
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    await message.answer(
        f"👑 <b>Админ-панель</b>\nВаш уровень: {level}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(level),
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu_cb(callback: CallbackQuery):
    level = await _get_level(callback.from_user.id)
    if not level:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        f"👑 <b>Админ-панель</b>\nВаш уровень: {level}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(level),
    )


# ── Верификация (level 1+) ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_verification")
async def admin_verification(callback: CallbackQuery, state: FSMContext):
    level = await _get_level(callback.from_user.id)
    if not level:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()

    async with async_session_maker() as session:
        reqs = await get_pending_verifications(session)

    if not reqs:
        await callback.message.answer("✅ Нет новых видео на проверку.", reply_markup=back_to_admin_kb())
        return

    await callback.message.answer(f"✅ <b>Видео на проверку: {len(reqs)}</b>", parse_mode="HTML")
    await state.set_state(AdminStates.verification_viewing)
    await state.update_data(verification_index=0, verification_reqs=[(r.id, r.user_id, r.video_id) for r in reqs])

    await _show_next_verification(callback.message, state)


async def _show_next_verification(message: Message, state: FSMContext):
    data = await state.get_data()
    reqs = data.get("verification_reqs", [])
    index = data.get("verification_index", 0)

    if index >= len(reqs):
        await message.answer("✅ Все видео проверены!", reply_markup=back_to_admin_kb())
        await state.clear()
        return

    req_id, user_id, video_id = reqs[index]

    async with async_session_maker() as session:
        user = await get_user(session, user_id)

    user_info = f"ID: {user_id}\nИмя: {user.first_name if user else '?'}\nВозраст: {user.age if user else '?'}"

    await message.answer_video(
        video_id,
        caption=f"<b>Видео #{index + 1} из {len(reqs)}</b>\n\n{user_info}",
        parse_mode="HTML",
        reply_markup=admin_verification_kb(),
    )

    await state.update_data(current_verification_id=req_id, current_user_id=user_id)


@router.callback_query(AdminStates.verification_viewing, F.data == "admin_verify_approve")
async def verify_approve(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    req_id = data.get("current_verification_id")

    async with async_session_maker() as session:
        await approve_verification(session, req_id)

    await callback.answer("✅ Видео одобрено.")
    data["verification_index"] = data.get("verification_index", 0) + 1
    await state.update_data(**data)
    await _show_next_verification(callback.message, state)


@router.callback_query(AdminStates.verification_viewing, F.data == "admin_verify_reject")
async def verify_reject(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    req_id = data.get("current_verification_id")

    async with async_session_maker() as session:
        await reject_verification(session, req_id)

    await callback.answer("❌ Видео отклонено.")
    data["verification_index"] = data.get("verification_index", 0) + 1
    await state.update_data(**data)
    await _show_next_verification(callback.message, state)


@router.callback_query(AdminStates.verification_viewing, F.data == "admin_verify_next")
async def verify_next(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data["verification_index"] = data.get("verification_index", 0) + 1
    await state.update_data(**data)
    await _show_next_verification(callback.message, state)


# ── Reports (level 1+) ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_reports")
async def admin_reports(callback: CallbackQuery):
    level = await _get_level(callback.from_user.id)
    if not level:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()

    async with async_session_maker() as session:
        reports = await get_open_reports(session)

    if not reports:
        await callback.message.answer("✅ Нет активных жалоб.", reply_markup=back_to_admin_kb())
        return

    await callback.message.answer(f"🚨 <b>Активные жалобы: {len(reports)}</b>", parse_mode="HTML")

    async with async_session_maker() as session:
        for r in reports:
            reporter = await get_user(session, r.reporter_id)
            reported = await get_user(session, r.reported_id)
            reporter_name = reporter.first_name if reporter else f"#{r.reporter_id}"
            reported_name = reported.first_name if reported else f"#{r.reported_id}"

            # Подсчитываем жалобы за 24ч
            count_24h = await count_reports_24h(session, r.reported_id)
            autobан_warning = f"\n⚠️ <b>АВТОБАН!</b> {count_24h}/5 жалоб за 24ч" if count_24h >= 5 else ""

            text = (
                f"🆔 Жалоба #{r.id}\n"
                f"От: {reporter_name} (ID: {r.reporter_id})\n"
                f"На: {reported_name} (ID: {r.reported_id})\n"
                f"Причина: {r.reason}\n"
                f"Дата: {r.created_at.strftime('%d.%m.%Y %H:%M')}"
                + autobан_warning
            )
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=admin_report_actions_kb(r.id, r.reported_id),
            )


@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban_user(callback: CallbackQuery):
    level = await _get_level(callback.from_user.id)
    if not level:
        await callback.answer("⛔", show_alert=True)
        return
    parts = callback.data.split("_")
    reported_id = int(parts[2])
    report_id = int(parts[3])

    async with async_session_maker() as session:
        await update_user(session, reported_id, is_banned=True)
        await resolve_report(session, report_id)

    logger.info(f"Admin {callback.from_user.id} banned user {reported_id}")
    await callback.answer(f"🚫 Пользователь {reported_id} заблокирован.", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data.startswith("admin_resolve_"))
async def admin_resolve_report(callback: CallbackQuery):
    level = await _get_level(callback.from_user.id)
    if not level:
        await callback.answer("⛔", show_alert=True)
        return
    report_id = int(callback.data.split("_")[2])

    async with async_session_maker() as session:
        await resolve_report(session, report_id)

    await callback.answer("✅ Жалоба отклонена.")
    await callback.message.delete()


# ── Promo creation (level 2+) ─────────────────────────────────────────────────

@router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_start(callback: CallbackQuery, state: FSMContext):
    level = await _get_level(callback.from_user.id)
    if not level or level < 2:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("🎟 Введите текст промокода:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.promo_waiting_code)


@router.message(AdminStates.promo_waiting_code)
async def admin_promo_code(message: Message, state: FSMContext):
    code = message.text.strip() if message.text else ""
    if not code:
        await message.answer("Введите корректный код.")
        return
    await state.update_data(promo_code=code)
    await message.answer("Сколько дней подписки даёт этот промокод?")
    await state.set_state(AdminStates.promo_waiting_days)


@router.message(AdminStates.promo_waiting_days)
async def admin_promo_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите положительное целое число дней.")
        return
    await state.update_data(promo_days=days)
    await message.answer("Максимальное количество активаций (0 = безлимит):")
    await state.set_state(AdminStates.promo_waiting_max_uses)


@router.message(AdminStates.promo_waiting_max_uses)
async def admin_promo_max_uses(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
        if max_uses < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите целое число ≥ 0.")
        return

    data = await state.get_data()
    async with async_session_maker() as session:
        from services.promo_service import create_promocode
        promo = await create_promocode(
            session,
            code=data["promo_code"],
            days=data["promo_days"],
            max_uses=max_uses,
            created_by=message.from_user.id,
        )

    await state.clear()
    limit_text = "безлимит" if max_uses == 0 else str(max_uses)
    logger.info(f"Admin {message.from_user.id} created promo: {promo.code}")
    await message.answer(
        f"✅ Промокод создан!\n\n"
        f"Код: <code>{promo.code}</code>\n"
        f"Дней: {promo.days}\n"
        f"Лимит: {limit_text}",
        parse_mode="HTML",
        reply_markup=back_to_admin_kb(),
    )


# ── Broadcast (level 2+) ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    level = await _get_level(callback.from_user.id)
    if not level or level < 2:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("📢 Введите текст рассылки:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.broadcast_waiting_text)


@router.message(AdminStates.broadcast_waiting_text)
async def admin_broadcast_text(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Введите текст.")
        return
    await state.update_data(broadcast_text=text)
    await message.answer(
        "Отправьте фото для рассылки или нажмите «Без фото»:",
        reply_markup=broadcast_photo_kb(),
    )
    await state.set_state(AdminStates.broadcast_waiting_photo)


@router.message(AdminStates.broadcast_waiting_photo, F.photo)
async def admin_broadcast_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    await state.clear()
    await _do_broadcast(message, data["broadcast_text"], photo_id)


@router.callback_query(AdminStates.broadcast_waiting_photo, F.data == "broadcast_no_photo")
async def admin_broadcast_no_photo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await callback.answer()
    await _do_broadcast(callback.message, data["broadcast_text"], None)


async def _do_broadcast(message: Message, text: str, photo_id: str | None):
    async with async_session_maker() as session:
        users = await get_all_non_lovaplus_users(session)

    sent = 0
    failed = 0
    for user in users:
        try:
            if photo_id:
                await message.bot.send_photo(user.user_id, photo_id, caption=text, parse_mode="HTML")
            else:
                await message.bot.send_message(user.user_id, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    logger.info(f"Broadcast done: sent={sent}, failed={failed}")
    await message.answer(
        f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=back_to_admin_kb(),
    )


# ── Stats (level 3) ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    level = await _get_level(callback.from_user.id)
    if not level or level < 3:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()

    async with async_session_maker() as session:
        stats = await get_stats(session)

    await callback.message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"💎 Активных LovaPlus: {stats['active_subs']}\n"
        f"❤️ Мэтчей сегодня: {stats['matches_today']}\n"
        f"🚨 Открытых жалоб: {stats['open_reports']}",
        parse_mode="HTML",
        reply_markup=back_to_admin_kb(),
    )


# ── Logs (level 3) ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_logs")
async def admin_logs_start(callback: CallbackQuery, state: FSMContext):
    level = await _get_level(callback.from_user.id)
    if not level or level < 3:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("Сколько последних строк показать? (1-200)", reply_markup=cancel_kb())
    await state.set_state(AdminStates.log_waiting_lines)


@router.message(AdminStates.log_waiting_lines)
async def admin_logs_show(message: Message, state: FSMContext):
    try:
        n = int(message.text.strip())
        n = max(1, min(n, 200))
    except (ValueError, AttributeError):
        n = 50
    await state.clear()
    tail = get_log_tail(n)
    MAX_LEN = 4000
    if len(tail) > MAX_LEN:
        tail = tail[-MAX_LEN:]
    await message.answer(f"<pre>{tail}</pre>", parse_mode="HTML", reply_markup=back_to_admin_kb())


# ── Manage admins (level 3) ───────────────────────────────────────────────────

@router.callback_query(F.data == "admin_manage_admins")
async def manage_admins(callback: CallbackQuery):
    level = await _get_level(callback.from_user.id)
    if not level or level < 3:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    async with async_session_maker() as session:
        admins = await get_all_admins(session)
    cfg = load_config()
    lines = [f"ID: {a.user_id}, Уровень: {a.level}" for a in admins]
    for uid, lvl in cfg.admins.items():
        if uid not in {a.user_id for a in admins}:
            lines.append(f"ID: {uid}, Уровень: {lvl} (из конфига)")
    text = "👑 <b>Список администраторов:</b>\n\n" + "\n".join(lines) if lines else "Нет админов в БД."
    await callback.message.answer(text, parse_mode="HTML", reply_markup=admin_manage_admins_kb())


@router.callback_query(F.data == "admin_add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите Telegram ID пользователя:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.admin_add_waiting_id)


@router.message(AdminStates.admin_add_waiting_id)
async def add_admin_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("Введите корректный ID (число).")
        return
    await state.update_data(new_admin_id=uid)
    await message.answer("Введите уровень доступа (1, 2 или 3):")
    await state.set_state(AdminStates.admin_add_waiting_level)


@router.message(AdminStates.admin_add_waiting_level)
async def add_admin_level(message: Message, state: FSMContext):
    try:
        level = int(message.text.strip())
        if level not in (1, 2, 3):
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите 1, 2 или 3.")
        return
    data = await state.get_data()
    uid = data["new_admin_id"]
    async with async_session_maker() as session:
        await add_admin(session, uid, level)
    await state.clear()
    logger.info(f"Admin {message.from_user.id} added admin {uid} level {level}")
    await message.answer(f"✅ Администратор {uid} с уровнем {level} добавлен.", reply_markup=back_to_admin_kb())


@router.callback_query(F.data == "admin_remove_admin")
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите Telegram ID администратора для удаления:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.admin_remove_waiting_id)


@router.message(AdminStates.admin_remove_waiting_id)
async def remove_admin_confirm(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("Введите корректный ID.")
        return
    async with async_session_maker() as session:
        success = await remove_admin(session, uid)
    await state.clear()
    if success:
        await message.answer(f"✅ Администратор {uid} удалён.", reply_markup=back_to_admin_kb())
    else:
        await message.answer(f"❌ Администратор {uid} не найден в БД.", reply_markup=back_to_admin_kb())


# ── Manual LovaPlus (level 3) ─────────────────────────────────────────────────

@router.callback_query(F.data == "admin_lovaplus")
async def admin_lovaplus_start(callback: CallbackQuery, state: FSMContext):
    level = await _get_level(callback.from_user.id)
    if not level or level < 3:
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        "💎 Введите Telegram ID пользователя:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminStates.lovaplus_waiting_user_id)


@router.message(AdminStates.lovaplus_waiting_user_id)
async def admin_lovaplus_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("Введите корректный ID.")
        return
    await state.update_data(target_user_id=uid)
    await message.answer(
        "Введите количество дней (положительное — добавить, 0 — отозвать LovaPlus):"
    )
    await state.set_state(AdminStates.lovaplus_waiting_days)


@router.message(AdminStates.lovaplus_waiting_days)
async def admin_lovaplus_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите 0 или положительное число.")
        return
    data = await state.get_data()
    uid = data["target_user_id"]
    await state.clear()

    async with async_session_maker() as session:
        if days == 0:
            await revoke_lovaplus(session, uid)
            msg = f"✅ LovaPlus отозван у пользователя {uid}."
        else:
            new_until = await add_lovaplus(session, uid, days)
            msg = f"✅ LovaPlus выдан пользователю {uid} до {new_until.strftime('%d.%m.%Y')}."

    logger.info(f"Admin {message.from_user.id} manual lovaplus: user={uid}, days={days}")
    await message.answer(msg, reply_markup=back_to_admin_kb())
