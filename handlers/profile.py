from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import async_session_maker
from keyboards.keyboards import my_profile_kb, search_filters_kb, blacklist_actions_kb, cancel_kb
from services.user_service import get_user, is_lovaplus_active, set_search_filters, reset_search_filters, get_blacklist, remove_from_blacklist
from states.states import FilterStates

router = Router()

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def format_date_ru(d: date) -> str:
    return f"{d.day} {MONTHS_RU[d.month]} {d.year} г."


@router.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        user = await get_user(session, user_id)

    if not user:
        await callback.message.answer("Профиль не найден.")
        return

    today = date.today()
    has_lovaplus = is_lovaplus_active(user)

    sub_text = (
        f"💎 LovaPlus до {format_date_ru(user.lovaplus_until)}" if has_lovaplus
        else "Без подписки (30 лайков/сутки)"
    )

    streak_text = f"🔥 Серия: {user.activity_streak} дней" if user.activity_streak else ""

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"Имя: {user.first_name}\n"
        f"Возраст: {user.age}\n"
        f"Город: {user.city}\n"
        f"О себе: {user.description}\n"
        f"Подписка: {sub_text}\n"
        f"Лайков сегодня: {user.likes_today}\n"
        + (f"{streak_text}\n" if streak_text else "")
        + (f"✅ Верифицирован\n" if user.is_verified else "")
    )

    photos = user.photo_ids or []
    if photos:
        await callback.message.answer_photo(
            photos[0],
            caption=text,
            parse_mode="HTML",
            reply_markup=my_profile_kb(has_lovaplus),
        )
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=my_profile_kb(has_lovaplus))


# ── Фильтры поиска ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "search_filters")
async def search_filters_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔍 <b>Фильтры поиска</b>\n\n"
        "Настройте параметры поиска (доступно только для LovaPlus):",
        parse_mode="HTML",
        reply_markup=search_filters_kb(),
    )


@router.callback_query(F.data == "filter_age")
async def filter_age_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введите минимальный возраст (или 0 для авто):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(FilterStates.waiting_age_min)


@router.message(FilterStates.waiting_age_min)
async def filter_age_min(message: Message, state: FSMContext):
    try:
        age_min = int(message.text.strip())
        if age_min < 0 or age_min > 100:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите число от 0 до 100.")
        return

    await state.update_data(filter_age_min=age_min if age_min > 0 else None)
    await message.answer("Введите максимальный возраст (или 0 для авто):")
    await state.set_state(FilterStates.waiting_age_max)


@router.message(FilterStates.waiting_age_max)
async def filter_age_max(message: Message, state: FSMContext):
    try:
        age_max = int(message.text.strip())
        if age_max < 0 or age_max > 100:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите число от 0 до 100.")
        return

    data = await state.get_data()
    age_min = data.get("filter_age_min")
    age_max = age_max if age_max > 0 else None

    async with async_session_maker() as session:
        await set_search_filters(session, message.from_user.id, age_min, age_max, None)

    await state.clear()
    await message.answer(
        f"✅ Фильтр по возрасту установлен:\n"
        f"От: {age_min or 'авто'} | До: {age_max or 'авто'}",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "filter_city")
async def filter_city_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введите город поиска (или напишите 'авто' для своего города):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(FilterStates.waiting_city)


@router.message(FilterStates.waiting_city)
async def filter_city_set(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city or len(city) > 100:
        await message.answer("Введите корректное название города.")
        return

    city = None if city.lower() == "авто" else city

    async with async_session_maker() as session:
        await set_search_filters(session, message.from_user.id, None, None, city)

    await state.clear()
    city_text = city or "ваш город"
    await message.answer(f"✅ Город установлен: {city_text}", parse_mode="HTML")


@router.callback_query(F.data == "filter_reset")
async def filter_reset(callback: CallbackQuery):
    await callback.answer()
    async with async_session_maker() as session:
        await reset_search_filters(session, callback.from_user.id)
    await callback.message.answer("✅ Все фильтры сброшены.")


# ── Чёрный список ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "blacklist_view")
async def blacklist_view(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        blacklist = await get_blacklist(session, user_id)

    if not blacklist:
        await callback.message.answer("Ваш чёрный список пуст.")
        return

    await callback.message.answer(f"🚫 <b>Чёрный список</b> ({len(blacklist)} пользователей):", parse_mode="HTML")

    async with async_session_maker() as session:
        for bl in blacklist:
            blocked_user = await get_user(session, bl.blocked_id)
            if blocked_user:
                text = f"👤 {blocked_user.first_name}, {blocked_user.age}\n🏙️ {blocked_user.city}"
                await callback.message.answer(
                    text,
                    reply_markup=blacklist_actions_kb(bl.blocked_id),
                )


@router.callback_query(F.data.startswith("blacklist_remove_"))
async def blacklist_remove(callback: CallbackQuery):
    blocked_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        success = await remove_from_blacklist(session, user_id, blocked_id)

    if success:
        await callback.answer("✅ Пользователь удалён из чёрного списка.")
        await callback.message.delete()
    else:
        await callback.answer("Не найдено.")


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=my_profile_kb(False),
    )
