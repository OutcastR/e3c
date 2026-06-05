from datetime import date, datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    ForeignKey, Integer, JSON, String, Text
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    photo_ids = Column(JSON, default=list)
    video_id = Column(String, nullable=True)           # file_id верификационного видео
    is_verified = Column(Boolean, default=False)       # прошёл видеоверификацию

    is_lovaplus = Column(Boolean, default=False)
    lovaplus_until = Column(Date, nullable=True)

    # Фильтры поиска (только для LovaPlus)
    filter_age_min = Column(Integer, nullable=True)    # None = авто
    filter_age_max = Column(Integer, nullable=True)
    filter_city = Column(String, nullable=True)        # None = свой город

    likes_today = Column(Integer, default=0)
    last_like_reset = Column(Date, default=date.today)
    profiles_viewed_since_last_warning = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Серия дней
    last_activity_date = Column(Date, nullable=True)   # дата последнего входа
    activity_streak = Column(Integer, default=0)       # текущая серия (дней)
    streak_boost_until = Column(DateTime, nullable=True)  # буст анкеты до этого времени

    # Антиспам
    likes_last_minute = Column(Integer, default=0)     # лайков за последнюю минуту
    last_like_time = Column(DateTime, nullable=True)   # время последнего лайка


class Like(Base):
    __tablename__ = 'likes'

    user_id = Column(BigInteger, primary_key=True)
    liked_user_id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PendingLike(Base):
    __tablename__ = 'pending_likes'

    user_id = Column(BigInteger, primary_key=True)
    target_id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_lovaplus_like = Column(Boolean, default=False)


class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(BigInteger, nullable=False)
    reported_id = Column(BigInteger, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)


class Blacklist(Base):
    """Чёрный список — только для LovaPlus."""
    __tablename__ = 'blacklist'

    user_id = Column(BigInteger, primary_key=True)      # кто заблокировал
    blocked_id = Column(BigInteger, primary_key=True)   # кого заблокировали
    created_at = Column(DateTime, default=datetime.utcnow)


class Promocode(Base):
    __tablename__ = 'promocodes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    days = Column(Integer, nullable=False)
    max_uses = Column(Integer, default=0)
    used_count = Column(Integer, default=0)
    created_by = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PromocodeUsage(Base):
    __tablename__ = 'promocode_usage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    promocode_id = Column(Integer, ForeignKey('promocodes.id'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)


class Admin(Base):
    __tablename__ = 'admins'

    user_id = Column(BigInteger, primary_key=True)
    level = Column(Integer, nullable=False)  # 1, 2, 3


class VerificationRequest(Base):
    """Заявки на видеоверификацию для модераторов."""
    __tablename__ = 'verification_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    video_id = Column(String, nullable=False)   # file_id видео
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='pending')  # pending / approved / rejected
