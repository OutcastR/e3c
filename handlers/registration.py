from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import async_session_maker
from keyboards.keyboards import confirmation_profile_kb, main_menu_kb, skip_photo_kb, verification_kb, cancel_kb
from services.user_service import create_user, get_user
from states.states import RegisterStates
from utils.logger import logger

router = Router()

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


async def start_registration(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(photos=[])
    await message.answer(
        "📸 <b>Шаг 1/5 — Фото</b>\n\nОтправьте первое фото для вашей анкеты:",
        parse_mode="HTML",
    )
    await state.set_state(RegisterStates.waiting_photo_1)


@router.message(RegisterStates.waiting_photo_1, F.photo)
async def reg_photo_1(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photos=[photo_id])
    await message.answer(
        "📸 Отлично! Хотите добавить второе фото?",
        reply_markup=skip_photo_kb(2),
    )
    await state.set_state(RegisterStates.waiting_photo_2)


@router.message(RegisterStates.waiting_photo_1)
async def reg_photo_1_bad(message: Message):
    await message.answer("Пожалуйста, отправьте фото (не файл, не текст).")


@router.message(RegisterStates.waiting_photo_2, F.photo)
async def reg_photo_2(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(
        "📸 Хотите добавить третье фото?",
        reply_markup=skip_photo_kb(3),
    )
    await state.set_state(RegisterStates.waiting_photo_3)


@router.callback_query(RegisterStates.waiting_photo_2, F.data == "skip_photo_2")
async def skip_photo_2(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("✏️ <b>Шаг 2/5 — Имя</b>\n\nВведите ваше имя:", parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_name)


@router.message(RegisterStates.waiting_photo_3, F.photo)
async def reg_photo_3(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer("✏️ <b>Шаг 2/5 — Имя</b>\n\nВведите ваше имя:", parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_name)


@router.callback_query(RegisterStates.waiting_photo_3, F.data == "skip_photo_3")
async def skip_photo_3(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("✏️ <b>Шаг 2/5 — Имя</b>\n\nВведите ваше имя:", parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_name)


@router.message(RegisterStates.waiting_photo_3)
async def reg_photo_3_bad(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, отправьте фото или нажмите кнопку «Пропустить».",
        reply_markup=skip_photo_kb(3),
    )


@router.message(RegisterStates.waiting_name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not name or len(name) > 50:
        await message.answer("Имя не должно быть пустым или длиннее 50 символов.")
        return
    await state.update_data(first_name=name)
    await message.answer("🎂 <b>Шаг 3/5 — Возраст</b>\n\nВведите ваш возраст (число):", parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_age)


@router.message(RegisterStates.waiting_age)
async def reg_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите корректный возраст (от 18 до 100).")
        return
    await state.update_data(age=age)
    await message.answer("🏙️ <b>Шаг 4/5 — Город</b>\n\nВ каком городе вы живёте?", parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_city)


@router.message(RegisterStates.waiting_city)
async def reg_city(message: Message, state: FSMContext):
    city = message.text.strip() if message.text else ""
    if not city or len(city) > 100:
        await message.answer("Введите корректное название города (до 100 символов).")
        return
    await state.update_data(city=city)
    await message.answer(
        "📝 <b>Шаг 5/5 — О себе</b>\n\nНапишите немного о себе (до 500 символов):",
        parse_mode="HTML",
    )
    await state.set_state(RegisterStates.waiting_description)


@router.message(RegisterStates.waiting_description)
async def reg_description(message: Message, state: FSMContext):
    desc = message.text.strip() if message.text else ""
    if not desc or len(desc) > 500:
        await message.answer("Описание не должно быть пустым или длиннее 500 символов.")
        return
    await state.update_data(description=desc)
    data = await state.get_data()

    text = (
        f"<b>Предварительный просмотр вашей анкеты:</b>\n\n"
        f"👤 <b>Имя:</b> {data['first_name']}\n"
        f"🎂 <b>Возраст:</b> {data['age']}\n"
        f"🏙️ <b>Город:</b> {data['city']}\n"
        f"📝 <b>О себе:</b> {data['description']}\n"
        f"📸 <b>Фото:</b> {len(data['photos'])} шт.\n\n"
        f"Всё верно?"
    )
    photos = data.get("photos", [])
    if photos:
        await message.answer_photo(photos[0], caption=text, parse_mode="HTML", reply_markup=confirm_profile_kb())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=confirm_profile_kb())


@router.callback_query(F.data == "confirm_profile")
async def confirm_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    user = callback.from_user

    async with async_session_maker() as session:
        await create_user(
            session,
            user_id=user.id,
            username=user.username,
            first_name=data["first_name"],
            age=data["age"],
            city=data["city"],
            description=data["description"],
            photo_ids=data.get("photos", []),
        )

    logger.info(f"New user registered: {user.id} (@{user.username})")

    # Предложить видеоверификацию
    await callback.message.answer(
        "🎉 <b>Анкета создана!</b>\n\n"
        "Давайте верифицируем вашу анкету с помощью видео — это повышает доверие к вам 🎥\n"
        "Снимите короткое видео (до 30 сек), где вы посмотрите в камеру и улыбнётесь.",
        parse_mode="HTML",
        reply_markup=verification_kb(),
    )
    await state.clear()
    await state.set_state(RegisterStates.waiting_video)


@router.callback_query(RegisterStates.waiting_video, F.data == "send_verification_video")
async def send_verification_video(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📹 Отправьте видео (до 30 секунд):",
        reply_markup=cancel_kb(),
    )


@router.message(RegisterStates.waiting_video, F.video)
async def video_received(message: Message, state: FSMContext):
    video_id = message.video.file_id
    await state.clear()

    async with async_session_maker() as session:
        from services.verification_service import create_verification_request
        await create_verification_request(session, message.from_user.id, video_id)

    await message.answer(
        "✅ Видео получено! Модераторы проверят вашу верификацию в течение 24 часов.\n\n"
        "Спасибо за использование Lovi Lova! ❤️",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(RegisterStates.waiting_video, F.data == "skip_verification")
async def skip_verification(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "Хорошо! Вы всегда сможете добавить видео позже.\n\nДобро пожаловать в Lovi Lova! ❤️",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "restart_registration")
async def restart_registration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_registration(callback.message, state)


def confirm_profile_kb():
    from keyboards.keyboards import confirm_profile_kb as real_kb
    return real_kb()
