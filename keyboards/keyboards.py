from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── Main Menu ──────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Найти пару", callback_data="search_start"),
        InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile"),
    )
    builder.row(
        InlineKeyboardButton(text="❤️ Кто меня лайкнул", callback_data="who_liked_me"),
        InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop"),
    )
    return builder.as_markup()


# ── Registration ───────────────────────────────────────────────────────────────

def skip_photo_kb(photo_num: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Пропустить фото", callback_data=f"skip_photo_{photo_num}"))
    return builder.as_markup()


def confirm_profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_profile"),
        InlineKeyboardButton(text="🔄 Заново", callback_data="restart_registration"),
    )
    return builder.as_markup()


def verification_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📹 Отправить видео", callback_data="send_verification_video"))
    builder.row(InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_verification"))
    return builder.as_markup()


# ── Search / Profiles ──────────────────────────────────────────────────────────

def search_actions_kb(target_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Lova ❤️", callback_data=f"like_{target_id}"),
        InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{target_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🚨 Пожаловаться", callback_data=f"report_{target_id}"),
        InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop"),
    )
    builder.row(
        InlineKeyboardButton(text="🚫 В чёрный список", callback_data=f"blacklist_add_{target_id}"),
    )
    return builder.as_markup()


# ── Report ─────────────────────────────────────────────────────────────────────

REPORT_REASONS = ["Мошенничество", "Неприемлемое поведение", "Спам", "Другое"]


def report_reasons_kb(target_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for reason in REPORT_REASONS:
        builder.row(InlineKeyboardButton(
            text=reason,
            callback_data=f"report_reason_{target_id}_{reason[:20]}"
        ))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_report"))
    return builder.as_markup()


def report_in_match_kb(target_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚨 Пожаловаться",
        callback_data=f"report_{target_id}"
    ))
    return builder.as_markup()


# ── Who liked me ──────────────────────────────────────────────────────────────

def liked_me_actions_kb(liker_id: int, is_expired: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_expired:
        builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_pending_{liker_id}"))
    else:
        builder.row(
            InlineKeyboardButton(text="Lova ❤️", callback_data=f"like_back_{liker_id}"),
            InlineKeyboardButton(text="👎 Пропустить", callback_data=f"skip_pending_{liker_id}"),
        )
    return builder.as_markup()


# ── Shop ───────────────────────────────────────────────────────────────────────

def shop_kb(has_subscription: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_subscription:
        builder.row(InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="buy_lovaplus"))
    else:
        builder.row(InlineKeyboardButton(text="💎 Купить LovaPlus", callback_data="buy_lovaplus"))
    builder.row(InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="enter_promo"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def buy_options_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="7 дней — 149₽", callback_data="pay_7"))
    builder.row(InlineKeyboardButton(text="1 месяц — 299₽", callback_data="pay_30"))
    builder.row(InlineKeyboardButton(text="3 месяца — 899₽", callback_data="pay_90"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="shop"))
    return builder.as_markup()


# ── My profile ────────────────────────────────────────────────────────────────

def my_profile_kb(has_lovaplus: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile"))
    if has_lovaplus:
        builder.row(InlineKeyboardButton(text="🔍 Фильтры поиска", callback_data="search_filters"))
        builder.row(InlineKeyboardButton(text="🚫 Чёрный список", callback_data="blacklist_view"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


# ── Фильтры поиска ────────────────────────────────────────────────────────────

def search_filters_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Возраст", callback_data="filter_age"))
    builder.row(InlineKeyboardButton(text="🏙️ Город", callback_data="filter_city"))
    builder.row(InlineKeyboardButton(text="🔄 Сбросить", callback_data="filter_reset"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="my_profile"))
    return builder.as_markup()


# ── Чёрный список ─────────────────────────────────────────────────────────────

def blacklist_actions_kb(blocked_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"blacklist_remove_{blocked_id}"))
    return builder.as_markup()


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_menu_kb(level: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Level 1+
    builder.row(InlineKeyboardButton(text="🚨 Жалобы", callback_data="admin_reports"))
    builder.row(InlineKeyboardButton(text="✅ Верификация", callback_data="admin_verification"))
    # Level 2+
    if level >= 2:
        builder.row(InlineKeyboardButton(text="🎟 Создать промокод", callback_data="admin_create_promo"))
        builder.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    # Level 3
    if level >= 3:
        builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
        builder.row(InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_manage_admins"))
        builder.row(InlineKeyboardButton(text="💎 Выдать/отозвать LovaPlus", callback_data="admin_lovaplus"))
        builder.row(InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs"))
    return builder.as_markup()


def admin_report_actions_kb(report_id: int, reported_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_ban_{reported_id}_{report_id}"),
        InlineKeyboardButton(text="✅ Отклонить", callback_data=f"admin_resolve_{report_id}"),
    )
    return builder.as_markup()


def admin_verification_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Одобрить", callback_data="admin_verify_approve"))
    builder.row(InlineKeyboardButton(text="❌ Отклонить", callback_data="admin_verify_reject"))
    builder.row(InlineKeyboardButton(text="⏭ Дальше", callback_data="admin_verify_next"))
    builder.row(InlineKeyboardButton(text="◀️ Меню", callback_data="admin_menu"))
    return builder.as_markup()


def admin_manage_admins_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin"))
    builder.row(InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove_admin"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"))
    return builder.as_markup()


def back_to_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="admin_menu"))
    return builder.as_markup()


def broadcast_photo_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Без фото — отправить", callback_data="broadcast_no_photo"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu"))
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()
