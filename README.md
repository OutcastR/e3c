# 💌 Lovi Lova — Telegram Dating Bot

Полнофункциональный Telegram-бот для знакомств на aiogram 3.x + SQLAlchemy 2.0.

## 🚀 Быстрый старт

### 1. Клонировать / распаковать проект

```bash
cd lovilova
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

```bash
cp .env.example .env
# Откройте .env и заполните BOT_TOKEN, ADMINS_LEVELS, PAYMENT_PROVIDER_TOKEN
```

Либо экспортируйте переменные напрямую:

```bash
export BOT_TOKEN="ваш_токен"
export ADMINS_LEVELS="ваш_id:3"
export PAYMENT_PROVIDER_TOKEN="тестовый_токен"
export DB_URL="sqlite+aiosqlite:///lovilova.db"
```

### 5. Запустить бота

```bash
python bot.py
```

При первом запуске таблицы создаются автоматически.

---

## 📁 Структура проекта

```
lovilova/
├── bot.py                  # Точка входа
├── requirements.txt
├── .env.example
├── database/
│   ├── models.py           # SQLAlchemy модели
│   └── engine.py           # Подключение к БД
├── handlers/
│   ├── start.py            # /start команда
│   ├── registration.py     # FSM регистрации
│   ├── search.py           # Поиск и лайки
│   ├── likes.py            # «Кто меня лайкнул»
│   ├── shop.py             # Магазин / LovaPlus / промокоды
│   ├── profile.py          # Мой профиль
│   ├── reports.py          # Жалобы
│   └── admin.py            # Админ-панель (3 уровня)
├── services/
│   ├── user_service.py     # Работа с пользователями
│   ├── like_service.py     # Лайки и мэтчи
│   ├── report_service.py   # Жалобы
│   ├── promo_service.py    # Промокоды
│   ├── admin_service.py    # Статистика, управление
│   └── background.py      # Фоновые задачи
├── keyboards/
│   └── keyboards.py        # Все inline-клавиатуры
├── states/
│   └── states.py           # FSM состояния
├── middlewares/
│   └── error_middleware.py # Обработка ошибок
├── utils/
│   ├── config.py           # Загрузка конфига
│   └── logger.py           # Логирование
└── logs/
    └── bot.log             # Лог-файл (создаётся автоматически)
```

---

## ⚙️ Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `BOT_TOKEN` | Токен от @BotFather | `123:ABC...` |
| `DB_URL` | URL базы данных | `sqlite+aiosqlite:///lovilova.db` |
| `PAYMENT_PROVIDER_TOKEN` | Токен платёжного провайдера | `381764678:TEST:xxx` |
| `ADMINS_LEVELS` | Список админов | `12345:3,67890:1` |

---

## 💎 LovaPlus — уровни и тарифы

| Тариф | Цена | Дней |
|---|---|---|
| 7 дней | 149₽ | 7 |
| 1 месяц | 299₽ | 30 |
| 3 месяца | 899₽ | 90 |

**Возможности LovaPlus:**
- Безлимит лайков
- Буст в поиске (показывается первым)
- Лайки без 3-часового ограничения
- Нет рекламных рассылок

---

## 👑 Уровни администраторов

| Уровень | Роль | Возможности |
|---|---|---|
| 1 | Модератор | Просмотр жалоб, бан/отклонение |
| 2 | Менеджер | + Создание промокодов, рассылки |
| 3 | Суперадмин | + Статистика, логи, управление админами, ручной LovaPlus |

---

## 🔄 Фоновые задачи

- **каждые 30 мин** — удаление просроченных pending_likes (обычные > 3ч)
- **ежедневно в 00:00 UTC** — сброс лимита лайков
- **ежедневно в 00:05 UTC** — деактивация истёкших подписок LovaPlus

---

## 💳 Интеграция платежей (ЮKassa)

1. Получите токен провайдера у @BotFather → Payments
2. Укажите его в `PAYMENT_PROVIDER_TOKEN`
3. Для тестов используйте тестовый токен от ЮKassa

---

## 🐘 PostgreSQL (продакшн)

```bash
DB_URL=postgresql+asyncpg://user:password@localhost:5432/lovilova
```

Установить драйвер уже включён в requirements.txt (`asyncpg`).

---

## 📋 Логирование

Логи пишутся в `logs/bot.log` с ротацией (5 MB × 5 файлов).
Критические ошибки отправляются суперадмину (первый с уровнем 3) в Telegram.
