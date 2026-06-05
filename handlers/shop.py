from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, LabeledPrice, Message,
    PreCheckoutQuery, SuccessfulPayment,
)

from database import async_session_maker
from keyboards.keyboards import buy_options_kb, cancel_kb, main_menu_kb, shop_kb
from services.promo_service import apply_promocode
from services.user_service import add_lovaplus, get_user, is_lovaplus_active
from states.states import PromoStates
from utils.logger import logger

router = Router()

PLANS = {
    "pay_7": {"days": 7, "price": 149, "label": "LovaPlus на 7 дней"},
    "pay_30": {"days": 30, "price": 299, "label": "LovaPlus на 1 месяц"},
    "pay_90": {"days": 90, "price": 899, "label": "LovaPlus на 3 месяца"},
}

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def format_date_ru(d: date) -> str:
    return f"{d.day} {MONTHS_RU[d.month]} {d.year} г."


async def show_shop(target: Message | CallbackQuery, user_id: int):
    async with async_session_maker() as session:
        user = await get_user(session, user_id)

    if not user:
        return

    today = date.today()
    has_sub = is_lovaplus_active(user)

    if has_sub:
        text = (
            "💎 <b>Ваша подписка LovaPlus</b>\n\n"
            f"Статус: Активна ✅\n"
            f"Действует до: {format_date_ru(user.lovaplus_until)}\n"
            f"Лимит лайков: безлимитный"
        )
    else:
        text = (
            "💎 <b>LovaPlus</b>\n\n"
            "У вас нет активной подписки LovaPlus\n"
            "Лимит лайков: 30/сутки\n\n"
            "<b>Преимущества LovaPlus:</b>\n"
            "• Безлимит лайков\n"
            "• Буст в поиске\n"
            "• Лайки без 3-часового ограничения\n"
            "• Без рекламных рассылок\n"
            "• Фильтры поиска\n"
            "• Чёрный список"
        )

    msg = target.message if isinstance(target, CallbackQuery) else target
    await msg.answer(text, parse_mode="HTML", reply_markup=shop_kb(bool(has_sub)))


@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery):
    await callback.answer()
    await show_shop(callback, callback.from_user.id)


@router.callback_query(F.data == "buy_lovaplus")
async def buy_lovaplus(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "💎 <b>Выберите период подписки:</b>",
        parse_mode="HTML",
        reply_markup=buy_options_kb(),
    )


@router.callback_query(F.data.in_({"pay_7", "pay_30", "pay_90"}))
async def initiate_payment(callback: CallbackQuery):
    await callback.answer()
    plan = PLANS[callback.data]
    from utils.config import load_config
    cfg = load_config()

    if not cfg.payment_provider_token:
        await callback.message.answer(
            "⚠️ Платёжная система временно недоступна. Обратитесь к администратору.",
            reply_markup=main_menu_kb(),
        )
        return

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"LovaPlus — {plan['label']}",
        description=f"Подписка LovaPlus: безлимит лайков, буст в поиске, без рекламы. {plan['label']}.",
        payload=f"lovaplus_{callback.data}_{callback.from_user.id}",
        provider_token=cfg.payment_provider_token,
        currency="RUB",
        prices=[LabeledPrice(label=plan['label'], amount=plan['price'] * 100)],
        start_parameter="lovaplus",
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    try:
        plan_suffix = f"pay_{parts[2]}"
        plan = PLANS.get(plan_suffix)
        if not plan:
            raise ValueError("Unknown plan")
    except Exception as e:
        logger.error(f"Payment payload parse error: {payload} — {e}")
        await message.answer("✅ Оплата прошла, но возникла ошибка. Обратитесь в поддержку.")
        return

    user_id = message.from_user.id
    async with async_session_maker() as session:
        new_until = await add_lovaplus(session, user_id, plan["days"])

    logger.info(f"Payment success: user {user_id}, plan {plan_suffix}, until {new_until}")
    await message.answer(
        f"🎉 <b>LovaPlus активирован!</b>\n\n"
        f"Подписка действует до: {format_date_ru(new_until)}\n"
        f"Наслаждайтесь безлимитными лайками! ❤️",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


# ── Promo ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "enter_promo")
async def enter_promo_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "🎟 <b>Введите промокод:</b>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(PromoStates.waiting_code)


@router.message(PromoStates.waiting_code)
async def enter_promo_code(message: Message, state: FSMContext):
    code = message.text.strip() if message.text else ""
    if not code:
        await message.answer("Введите текст промокода.")
        return

    async with async_session_maker() as session:
        success, msg_text = await apply_promocode(session, code, message.from_user.id)

    await state.clear()
    await message.answer(msg_text, parse_mode="HTML", reply_markup=main_menu_kb())
