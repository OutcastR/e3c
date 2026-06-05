import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from database import init_db
from handlers import admin, likes, profile, registration, reports, search, shop, start
from middlewares.error_middleware import ErrorMiddleware
from services.background import start_background_tasks
from utils.config import load_config
from utils.logger import logger


async def main():
    # Загружаем конфиг из переменных окружения или задаём вручную
    BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8416323639:AAGWVL9tg57MTZakEmZM71hYNyNSf_mF764"
    ADMIN_ID = os.environ.get("ADMIN_ID") or "992295328"
    
    # Устанавливаем переменные для load_config()
    os.environ["BOT_TOKEN"] = BOT_TOKEN
    os.environ["ADMINS_LEVELS"] = f"{ADMIN_ID}:3"
    os.environ["PAYMENT_PROVIDER_TOKEN"] = os.environ.get("PAYMENT_PROVIDER_TOKEN", "")
    os.environ["DB_URL"] = os.environ.get("DB_URL", "sqlite+aiosqlite:///lovilova.db")
    
    cfg = load_config()

    logger.info("Starting Lovi Lova bot...")
    logger.info(f"Bot Token: {BOT_TOKEN[:20]}...")
    logger.info(f"Admin ID: {ADMIN_ID}")

    # Init DB
    await init_db(cfg.db_url)
    logger.info(f"Database initialized: {cfg.db_url}")

    # Init bot and dispatcher
    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.update.middleware(ErrorMiddleware(developer_id=cfg.developer_id))

    # Register routers
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(search.router)
    dp.include_router(likes.router)
    dp.include_router(shop.router)
    dp.include_router(profile.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)

    # Background tasks
    tasks = start_background_tasks()

    logger.info("Bot is running. Press Ctrl+C to stop.")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for task in tasks:
            task.cancel()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
