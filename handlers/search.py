from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from database import async_session_maker
from keyboards.keyboards import search_actions_kb, main_menu_kb
from services.like_service import record_like
from services.user_service import (
    can_like, check_antispam, get_next_profile, get_user,
    increment_likes_today, increment_profiles_viewed, is_lovaplus_active, record_activity, has_streak_boost,
)
from states.states import SearchStates
from utils.logger import logger

router = Router()

SAFETY_WARNING = (
    "🔒 <b>Напоминание о безопасности</b>\n\n"
    "❌ Не переводите деньги незнакомцам.\n"
    "❌ Не делитесь личными данными (паспорт, адрес).\n"
    "✅ При подозрениях жмите «Пожаловаться».\n\n"
    "Берегите себя ❤️"
)


def profile_text(user) -> str:
    text = f"👤 <b>{user.first_name}</b>, {user.age} лет\n"
    text += f"🏙️ {user.city}\n"
    text += f"📝 {user.description}\n"
    
    # Теги
    tags = []
    if user.is_verified:
        tags.append("✅ Верифицирован")
    if is_lovaplus_active(user):
        tags.append("💎 LovaPlus")
    if has_streak_boost(user):
        tags.append("🔥 В тренде")
    
    if tags:
        text += "\n" + " | ".join(tags)
    
    return text


@router.callback_query(F.data == "search_start")
async def search_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SearchStates.browsing)
    await state.update_data(seen=[])
    
    # Записываем активность (для серии дней)
    async with async_session_maker() as session:
        boost_hours = await record_activity(session, callback.from_user.id)
    
    if boost_hours:
        await callback.message.answer(
            f"🔥 <b>Достижение!</b>\n\n"
            f"Вы активны {boost_hours} дней подряд!\n"
            f"Ваша анкета получит буст в поиске на {boost_hours} часов.",
            parse_mode="HTML",
        )
    
    await _show_next_profile(callback.message, state, callback.from_user.id)


async def _show_next_profile(message: Message, state: FSMContext, user_id: int, edit: bool = False):
    async with async_session_maker() as session:
        user = await get_user(session, user_id)
        if not user:
            await message.answer("Профиль не найден.", reply_markup=main_menu_kb())
            return

        if user.is_banned:
            await message.answer("🚫 Ваш аккаунт заблокирован.", reply_markup=main_menu_kb())
            await state.clear()
            return

        data = await state.get_data()
        seen = data.get("seen", [])

        target = await get_next_profile(session, user, seen)

    if not target:
        await message.answer(
            "😔 <b>Анкеты закончились</b>\n\nВ вашем городе больше нет подходящих анкет. Загляните позже!",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    seen.append(target.user_id)
    await state.update_data(seen=seen)

    # Check safety warning
    async with async_session_maker() as session:
        should_warn = await increment_profiles_viewed(session, user_id)

    if should_warn:
        await message.answer(SAFETY_WARNING, parse_mode="HTML")

    text = profile_text(target)
    kb = search_actions_kb(target.user_id)

    photos = target.photo_ids or []
    if photos:
        if edit:
            try:
                await message.edit_media(
                    InputMediaPhoto(media=photos[0], caption=text, parse_mode="HTML"),
                    reply_markup=kb,
                )
                return
            except Exception:
                pass
        await message.answer_photo(photos[0], caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        if edit:
            try:
                await message.edit_text(text, parse_mode="HTML", reply_markup=kb)
                return
            except Exception:
                pass
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("like_"), ~F.data.startswith("like_back_"))
async def handle_like(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[1])
    from_id = callback.from_user.id

    async with async_session_maker() as session:
        user = await get_user(session, from_id)
        if not user:
            await callback.answer("Профиль не найден.", show_alert=True)
            return

        # Антиспам проверка
        allowed, reason = await check_antispam(session, user)
        if not allowed:
            await callback.answer(reason, show_alert=True)
            return

        if not await can_like(session, user):
            await callback.answer(
                "⚠️ Вы исчерпали дневной лимит (30 лайков). Оформите LovaPlus для безлимита!",
                show_alert=True,
            )
            return

        is_lovaplus_like = is_lovaplus_active(user)
        is_match, already = await record_like(session, from_id, target_id, is_lovaplus_like)

        if not already:
            await increment_likes_today(session, from_id)

        if is_match:
            target = await get_user(session, target_id)
            target_username = f"@{target.username}" if target and target.username else f"пользователь #{target_id}"
            user_username = f"@{user.username}" if user.username else f"пользователь #{from_id}"

            match_text = (
                "🎉 <b>Взаимная симпатия!</b>\n\n"
                f"Вы можете пообщаться с {target_username}\n\n"
                "⚠️ Не переводите деньги, не делитесь личными данными. "
                "При подозрениях нажмите «Пожаловаться»."
            )
            match_text_for_target = (
                "🎉 <b>Взаимная симпатия!</b>\n\n"
                f"Вы можете пообщаться с {user_username}\n\n"
                "⚠️ Не переводите деньги, не делитесь личными данными. "
                "При подозрениях нажмите «Пожаловаться»."
            )

            from keyboards.keyboards import report_in_match_kb
            await callback.message.answer(match_text, parse_mode="HTML", reply_markup=report_in_match_kb(target_id))
            try:
                await callback.bot.send_message(
                    target_id, match_text_for_target,
                    parse_mode="HTML",
                    reply_markup=report_in_match_kb(from_id),
                )
            except Exception as e:
                logger.warning(f"Could not send match notification to {target_id}: {e}")

            logger.info(f"Match: {from_id} <-> {target_id}")
        else:
            if not already:
                target = await get_user(session, target_id)
                if target:
                    note = (
                        "💌 <b>Вас лайкнули!</b>\n\n"
                        + ("У вас есть 3 часа, чтобы ответить, иначе интерес пропадёт." if not is_lovaplus_like else "Пользователь с LovaPlus лайкнул вас — интерес не исчезнет!")
                    )
                    try:
                        await callback.bot.send_message(target_id, note, parse_mode="HTML")
                    except Exception as e:
                        logger.warning(f"Could not notify {target_id} of like: {e}")

    await callback.answer("❤️ Лайк отправлен!")
    await _show_next_profile(callback.message, state, from_id, edit=True)


@router.callback_query(F.data.startswith("dislike_"))
async def handle_dislike(callback: CallbackQuery, state: FSMContext):
    await callback.answer("👎")
    await _show_next_profile(callback.message, state, callback.from_user.id, edit=True)


@router.callback_query(F.data.startswith("blacklist_add_"))
async def blacklist_add(callback: CallbackQuery):
    blocked_id = int(callback.data.split("_")[2])
    from_id = callback.from_user.id

    async with async_session_maker() as session:
        user = await get_user(session, from_id)
        if not is_lovaplus_active(user):
            await callback.answer(
                "🔒 Чёрный список доступен только для LovaPlus.",
                show_alert=True,
            )
            return

        from services.user_service import add_to_blacklist
        success = await add_to_blacklist(session, from_id, blocked_id)

    if success:
        await callback.answer("✅ Пользователь добавлен в чёрный список.")
    else:
        await callback.answer("Пользователь уже в чёрном списке.")


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
