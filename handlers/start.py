from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import async_session_maker
from keyboards.keyboards import main_menu_kb
from services.user_service import get_user, is_registered, update_user
from handlers.registration import start_registration
from utils.logger import logger

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = message.from_user

    if not user.username:
        await message.answer(
            "⚠️ <b>Необходим @username</b>\n\n"
            "Для использования Lovi Lova у вас должен быть установлен username в настройках Telegram.\n"
            "Установите его в <b>Настройки → Изменить профиль → Имя пользователя</b> и нажмите /start снова.",
            parse_mode="HTML",
        )
        return

    async with async_session_maker() as session:
        registered = await is_registered(session, user.id)

        if registered:
            await update_user(session, user.id, username=user.username)
            db_user = await get_user(session, user.id)

            if db_user and db_user.is_banned:
                await message.answer(
                    "🚫 Ваш аккаунт заблокирован за нарушение правил сервиса."
                )
                return

    if registered:
        logger.info(f"User {user.id} (@{user.username}) started bot (existing)")
        await message.answer(
            f"👋 С возвращением, <b>{message.from_user.first_name}</b>!\n\nЧем займёмся сегодня?",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
    else:
        logger.info(f"New user {user.id} (@{user.username}) started registration")
        await message.answer(
            "💌 <b>Добро пожаловать в Lovi Lova!</b>\n\n"
            "Lovi Lova — место, где происходят настоящие встречи ❤️\n\n"
            "Давайте создадим вашу анкету! Это займёт пару минут.",
            parse_mode="HTML",
        )
        await start_registration(message, state)
