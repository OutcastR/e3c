import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from utils.logger import logger


class ErrorMiddleware(BaseMiddleware):
    def __init__(self, developer_id: int = 0):
        self.developer_id = developer_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Unhandled exception: {e}\n{tb}")

            if self.developer_id:
                try:
                    bot = data.get("bot")
                    if bot:
                        await bot.send_message(
                            self.developer_id,
                            f"🔴 <b>Критическая ошибка</b>\n\n<pre>{tb[-3000:]}</pre>",
                            parse_mode="HTML",
                        )
                except Exception as send_err:
                    logger.error(f"Could not notify developer: {send_err}")

            # Try to notify user
            update: Update = event if isinstance(event, Update) else None
            if update:
                chat_id = None
                if update.message:
                    chat_id = update.message.chat.id
                elif update.callback_query:
                    chat_id = update.callback_query.message.chat.id
                if chat_id:
                    try:
                        bot = data.get("bot")
                        if bot:
                            await bot.send_message(chat_id, "⚠️ Произошла внутренняя ошибка. Попробуйте позже.")
                    except Exception:
                        pass
