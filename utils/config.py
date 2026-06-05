import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Config:
    bot_token: str
    db_url: str
    payment_provider_token: str
    admins: Dict[int, int] = field(default_factory=dict)  # {user_id: level}
    developer_id: int = 0  # first level-3 admin receives critical errors


def load_config() -> Config:
    bot_token = os.environ["BOT_TOKEN"]
    db_url = os.environ.get("DB_URL", "sqlite+aiosqlite:///lovilova.db")
    payment_provider_token = os.environ.get("PAYMENT_PROVIDER_TOKEN", "")
    admins_raw = os.environ.get("ADMINS_LEVELS", "")

    admins: Dict[int, int] = {}
    if admins_raw:
        for pair in admins_raw.split(","):
            pair = pair.strip()
            if ":" in pair:
                uid_str, lvl_str = pair.split(":", 1)
                try:
                    admins[int(uid_str.strip())] = int(lvl_str.strip())
                except ValueError:
                    pass

    developer_id = 0
    for uid, lvl in admins.items():
        if lvl == 3:
            developer_id = uid
            break

    return Config(
        bot_token=bot_token,
        db_url=db_url,
        payment_provider_token=payment_provider_token,
        admins=admins,
        developer_id=developer_id,
    )
