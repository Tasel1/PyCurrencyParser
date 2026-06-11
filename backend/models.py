from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    settings = relationship("UserSetting", back_populates="user")


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String)
    value = Column(String)

    user = relationship("User", back_populates="settings")


class CurrencyHistory(Base):
    __tablename__ = "currency_history"

    id = Column(Integer, primary_key=True, index=True)
    currency = Column(String)
    rate = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
