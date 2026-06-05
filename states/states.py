from aiogram.fsm.state import State, StatesGroup


class RegisterStates(StatesGroup):
    waiting_photo_1 = State()
    waiting_photo_2 = State()
    waiting_photo_3 = State()
    waiting_name = State()
    waiting_age = State()
    waiting_city = State()
    waiting_description = State()
    waiting_video = State()  # видеоверификация


class SearchStates(StatesGroup):
    browsing = State()


class ReportStates(StatesGroup):
    choosing_reason = State()


class PromoStates(StatesGroup):
    waiting_code = State()


class FilterStates(StatesGroup):
    waiting_age_min = State()
    waiting_age_max = State()
    waiting_city = State()


class BlacklistStates(StatesGroup):
    viewing = State()


class AdminStates(StatesGroup):
    # Level 1: verification
    verification_choosing = State()
    verification_viewing = State()

    # Level 2+: create promocode
    promo_waiting_code = State()
    promo_waiting_days = State()
    promo_waiting_max_uses = State()

    # Level 2+: broadcast
    broadcast_waiting_text = State()
    broadcast_waiting_photo = State()

    # Level 3: manage admins
    admin_add_waiting_id = State()
    admin_add_waiting_level = State()
    admin_remove_waiting_id = State()

    # Level 3: manual lovaplus
    lovaplus_waiting_user_id = State()
    lovaplus_waiting_days = State()

    # Level 3: log lines
    log_waiting_lines = State()
