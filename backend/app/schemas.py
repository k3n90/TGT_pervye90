from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class CardCreate(BaseModel):
    full_name: str = Field(min_length=5, max_length=120)
    position_code: str
    location_id: int
    start_date: date
    probation_days: int
    first_shift_schedule: str = Field(min_length=3, max_length=300)
    mentor_id: Optional[int] = None
    manager_id: int
    hire_source: str = Field(min_length=2, max_length=120)
    shared_warehouse: bool = False


class CardPatch(BaseModel):
    mentor_id: Optional[int] = None
    clear_mentor: bool = False
    first_shift_schedule: Optional[str] = None
    hire_source: Optional[str] = None


class MarkIn(BaseModel):
    mark: Literal["yes", "not_yet"]


class PulseIn(BaseModel):
    day: Literal[7, 30]
    q1: Literal["yes", "mid", "no"]
    q2: Literal["yes", "mid", "no"]
    q3: Literal["yes", "mid", "no"]
    comment: str = ""


class AdmissionIn(BaseModel):
    value: Literal["yes", "caveat", "none"]
    note: str = ""


class Day30In(BaseModel):
    choice: Literal["independent", "still_with_mentor", "role_unfit"]
    reason: str = ""
    recheck_date: Optional[date] = None


class Day60In(BaseModel):
    stable: bool
    note: str = ""


class DecisionIn(BaseModel):
    decision: Literal["confirm", "separate", "transfer"]
    comment: str = Field(min_length=8, max_length=500)
    dismissed_date: Optional[date] = None
    transfer_title: str = ""


class ResolveIn(BaseModel):
    resolution: Literal["fixed", "recheck", "separation"]
    comment: str = ""
    recheck_date: Optional[date] = None
    dismissed_date: Optional[date] = None


class TemplateCreate(BaseModel):
    title: str = Field(min_length=8, max_length=300)
    checkpoint_day: Literal[1, 7, 14, 30]
    is_critical: bool = False


class TemplatePatch(BaseModel):
    is_active: Optional[bool] = None
    is_critical: Optional[bool] = None
