from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))

    locations: Mapped[list[Location]] = relationship(back_populates="department")
    tracks: Mapped[list[Track]] = relationship(back_populates="department")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(180))

    department: Mapped[Department] = relationship(back_populates="locations")


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    independence_day: Mapped[int] = mapped_column(Integer)

    department: Mapped[Department] = relationship(back_populates="tracks")
    positions: Mapped[list[Position]] = relationship(back_populates="track")
    templates: Mapped[list[ChecklistTemplate]] = relationship(back_populates="track")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))

    track: Mapped[Track] = relationship(back_populates="positions")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(160))
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.id"), nullable=True)

    location: Mapped[Optional[Location]] = relationship()
    departments: Mapped[list[Department]] = relationship(secondary="user_departments")


class UserDepartment(Base):
    __tablename__ = "user_departments"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), primary_key=True)


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    checkpoint_day: Mapped[int] = mapped_column(Integer)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    include_mode: Mapped[str] = mapped_column(String(32))
    position_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(400))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    track: Mapped[Track] = relationship(back_populates="templates")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"))
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    start_date: Mapped[date] = mapped_column(Date)
    probation_days: Mapped[int] = mapped_column(Integer)
    probation_end_date: Mapped[date] = mapped_column(Date)
    first_shift_schedule: Mapped[str] = mapped_column(String(300))
    mentor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    mentor_assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stage: Mapped[str] = mapped_column(String(32), default="waiting")
    admission: Mapped[str] = mapped_column(String(16), default="none")
    admission_note: Mapped[str] = mapped_column(String(500), default="")
    admission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    day30_choice: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    day30_reason: Mapped[str] = mapped_column(String(500), default="")
    day30_recheck_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    day60_stable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    day60_note: Mapped[str] = mapped_column(String(500), default="")
    probation_decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    probation_decision_comment: Mapped[str] = mapped_column(String(500), default="")
    probation_decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    transfer_title: Mapped[str] = mapped_column(String(160), default="")
    dismissed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    separation_started: Mapped[bool] = mapped_column(Boolean, default=False)
    hire_source: Mapped[str] = mapped_column(String(120), default="")
    shared_warehouse: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    position: Mapped[Position] = relationship()
    track: Mapped[Track] = relationship()
    department: Mapped[Department] = relationship()
    location: Mapped[Location] = relationship()
    mentor: Mapped[Optional[User]] = relationship(foreign_keys=[mentor_id])
    manager: Mapped[User] = relationship(foreign_keys=[manager_id])
    items: Mapped[list[CardItem]] = relationship(back_populates="card", cascade="all, delete-orphan")
    checkpoints: Mapped[list[Checkpoint]] = relationship(back_populates="card", cascade="all, delete-orphan")
    pulses: Mapped[list[Pulse]] = relationship(back_populates="card", cascade="all, delete-orphan")
    signals: Mapped[list[Signal]] = relationship(back_populates="card", cascade="all, delete-orphan")
    events: Mapped[list[Event]] = relationship(back_populates="card", cascade="all, delete-orphan")


class CardItem(Base):
    __tablename__ = "card_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    code: Mapped[str] = mapped_column(String(64))
    checkpoint_day: Mapped[int] = mapped_column(Integer)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String(400))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    mark: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)

    card: Mapped[Card] = relationship(back_populates="items")


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    __table_args__ = (UniqueConstraint("card_id", "day_number", name="uq_checkpoint_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    day_number: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    card: Mapped[Card] = relationship(back_populates="checkpoints")


class Pulse(Base):
    __tablename__ = "pulses"
    __table_args__ = (UniqueConstraint("card_id", "day_number", name="uq_pulse_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    day_number: Mapped[int] = mapped_column(Integer)
    q1: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    q2: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    q3: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    comment: Mapped[str] = mapped_column(String(500), default="")
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    recorded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    card: Mapped[Card] = relationship(back_populates="pulses")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(180))
    detail: Mapped[str] = mapped_column(String(600))
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    resolution: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    comment: Mapped[str] = mapped_column(String(500), default="")
    fingerprint: Mapped[str] = mapped_column(String(300), default="")
    recheck_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    due_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    card: Mapped[Card] = relationship(back_populates="signals")
    owner: Mapped[Optional[User]] = relationship()


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    actor_name: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(String(500))

    card: Mapped[Card] = relationship(back_populates="events")


class BaselinePerson(Base):
    __tablename__ = "baseline_people"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    started_on: Mapped[date] = mapped_column(Date)
    left_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    department: Mapped[Department] = relationship()


class AppState(Base):
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    note: Mapped[str] = mapped_column(Text, default="")
