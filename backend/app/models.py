from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    events: Mapped[list["Event"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class UserAIProviderKeys(Base):
    __tablename__ = "user_ai_provider_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    gemini_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    groq_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(40), default="Wedding")
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    venue: Mapped[str] = mapped_column(String(200), default="Choose your venue")
    location: Mapped[str] = mapped_column(String(160), default="Not set yet")
    guest_count: Mapped[int] = mapped_column(Integer, default=120)
    budget: Mapped[float] = mapped_column(Float, default=250000)
    theme: Mapped[str] = mapped_column(String(80), default="Garden romance")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    owner: Mapped[User] = relationship(back_populates="events")
    tasks: Mapped[list["Task"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    vendors: Mapped[list["Vendor"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    guests: Mapped[list["Guest"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="event", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(60), default="General")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="To do")
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    event: Mapped[Event] = relationship(back_populates="tasks")

class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(140))
    category: Mapped[str] = mapped_column(String(60))
    quote: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(24), default="Researching")
    rating: Mapped[float] = mapped_column(Float, default=0)
    contact: Mapped[str] = mapped_column(String(180), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    event: Mapped[Event] = relationship(back_populates="vendors")

class Guest(Base):
    __tablename__ = "guests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(140))
    email: Mapped[str] = mapped_column(String(255), default="")
    group_name: Mapped[str] = mapped_column(String(80), default="Friends")
    rsvp: Mapped[str] = mapped_column(String(20), default="Pending")
    plus_one: Mapped[bool] = mapped_column(Boolean, default=False)
    dietary: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    event: Mapped[Event] = relationship(back_populates="guests")

class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    planned: Mapped[float] = mapped_column(Float, default=0)
    spent: Mapped[float] = mapped_column(Float, default=0)
    color: Mapped[str] = mapped_column(String(20), default="#D58F7A")
    event: Mapped[Event] = relationship(back_populates="expenses")
