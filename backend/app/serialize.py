from __future__ import annotations

from datetime import date, datetime

from app.content import (
    ADMISSION_LABELS,
    ANSWER_LABELS,
    DAY30_LABELS,
    DECISION_LABELS,
    QUESTIONS,
    RESOLUTION_LABELS,
    ROLE_LABELS,
    STAGE_LABELS,
)
from app.dates import next_working_day, window_status
from app.logic import (
    FLOOR_TRACKS,
    JUDGMENT_CODES,
    can_edit_items,
    can_manage,
    critical_count,
    day_reached,
    decision_unlocked,
    editable,
    today,
)
from app.models import Card, Signal, User


def _iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _person(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": user.id, "full_name": user.full_name, "role": user.role, "title": user.title}


def checkpoint_view(card: Card, checkpoint, current: date) -> dict:
    if checkpoint.completed_at:
        on_time = checkpoint.completed_at.date() <= next_working_day(checkpoint.due_date)
        status = "done" if on_time else "done_late"
    elif card.stage in ("closed", "dismissed"):
        status = "skipped"
    else:
        status = window_status(checkpoint.due_date, current)
    if checkpoint.is_final and card.probation_days <= 0:
        label = "Подтверждение выхода"
    elif checkpoint.is_final:
        label = "Решение по испытанию"
    elif checkpoint.day_number == 14 and card.track.code in FLOOR_TRACKS:
        label = "Допуск к типовой операции"
    elif checkpoint.day_number == 30:
        label = "Решение руководителя"
    elif checkpoint.day_number == 60:
        label = "Устойчивость смены"
    elif checkpoint.day_number == 1:
        label = "Первая смена"
    else:
        label = f"{checkpoint.day_number}-й день"
    return {
        "day": checkpoint.day_number,
        "due_date": checkpoint.due_date.isoformat(),
        "is_final": checkpoint.is_final,
        "label": label,
        "status": status,
        "completed_at": _iso(checkpoint.completed_at),
    }


def signal_view(signal: Signal, user: User, card: Card, current: date) -> dict:
    allow_fixed = signal.code in JUDGMENT_CODES
    can_resolve = signal.status == "open" and signal.severity == "red" and (
        user.role == "hr" or can_manage(user, card) or signal.owner_id == user.id
    )
    if card.stage in ("closed", "dismissed"):
        can_resolve = False
    return {
        "id": signal.id,
        "code": signal.code,
        "severity": signal.severity,
        "title": signal.title,
        "detail": signal.detail,
        "status": signal.status,
        "owner": _person(signal.owner),
        "due_date": _iso(signal.due_at),
        "opened_at": _iso(signal.opened_at),
        "recheck_date": _iso(signal.recheck_date),
        "resolution": signal.resolution,
        "resolution_label": RESOLUTION_LABELS.get(signal.resolution or "", ""),
        "comment": signal.comment,
        "resolved_at": _iso(signal.resolved_at),
        "overdue": bool(signal.status == "open" and signal.due_at and current > signal.due_at),
        "allow_fixed": allow_fixed,
        "can_resolve": can_resolve,
        "needs_action": signal.severity == "red" and signal.status == "open",
    }


def card_brief(card: Card, current: date | None = None) -> dict:
    current = current or today()
    reds = [s for s in card.signals if s.status == "open" and s.severity == "red"]
    yellows = [s for s in card.signals if s.status == "open" and s.severity == "yellow"]
    return {
        "id": card.id,
        "full_name": card.full_name,
        "position_name": card.position.name,
        "track_code": card.track.code,
        "track_name": card.track.name,
        "location_name": card.location.name,
        "department_name": card.department.name,
        "start_date": card.start_date.isoformat(),
        "probation_end_date": card.probation_end_date.isoformat(),
        "stage": card.stage,
        "stage_label": STAGE_LABELS.get(card.stage, card.stage),
        "mentor_name": card.mentor.full_name if card.mentor else None,
        "manager_name": card.manager.full_name,
        "admission": card.admission,
        "admission_label": ADMISSION_LABELS.get(card.admission, card.admission),
        "red_count": len(reds),
        "yellow_count": len(yellows),
        "separation_started": card.separation_started,
    }


def card_detail(card: Card, user: User) -> dict:
    current = today()
    manage = can_manage(user, card)
    edit_items = can_edit_items(user, card)
    unlocked = decision_unlocked(card)
    signals = sorted(card.signals, key=lambda row: row.opened_at or datetime.min, reverse=True)
    events = sorted(card.events, key=lambda row: row.created_at)
    items = sorted(card.items, key=lambda row: (row.checkpoint_day, row.sort_order))
    data = card_brief(card, current)
    data.update(
        {
            "position_code": card.position.code,
            "probation_days": card.probation_days,
            "first_shift_schedule": card.first_shift_schedule,
            "hire_source": card.hire_source,
            "shared_warehouse": card.shared_warehouse,
            "critical_count": critical_count(card),
            "critical_limit": 5,
            "mentor": _person(card.mentor),
            "manager": _person(card.manager),
            "admission_note": card.admission_note,
            "admission_date": _iso(card.admission_date),
            "day30_choice": card.day30_choice,
            "day30_choice_label": DAY30_LABELS.get(card.day30_choice or "", ""),
            "day30_reason": card.day30_reason,
            "day30_recheck_date": _iso(card.day30_recheck_date),
            "day60_stable": card.day60_stable,
            "day60_note": card.day60_note,
            "probation_decision": card.probation_decision,
            "probation_decision_label": DECISION_LABELS.get(card.probation_decision or "", ""),
            "probation_decision_comment": card.probation_decision_comment,
            "probation_decision_date": _iso(card.probation_decision_date),
            "transfer_title": card.transfer_title,
            "dismissed_date": _iso(card.dismissed_date),
            "questions": [{"code": code, "text": text} for code, text in QUESTIONS],
            "answer_labels": ANSWER_LABELS,
            "items": [
                {
                    "id": item.id,
                    "code": item.code,
                    "day": item.checkpoint_day,
                    "title": item.title,
                    "is_critical": item.is_critical,
                    "mark": item.mark,
                    "fail_count": item.fail_count,
                    "can_mark": edit_items and day_reached(card, item.checkpoint_day, current),
                    "due_date": card.start_date.fromordinal(card.start_date.toordinal() + item.checkpoint_day - 1).isoformat(),
                }
                for item in items
            ],
            "checkpoints": [
                checkpoint_view(card, checkpoint, current)
                for checkpoint in sorted(card.checkpoints, key=lambda row: row.day_number)
            ],
            "pulses": [_pulse_view(card, day, edit_items, current) for day in (7, 30) if any(p.day_number == day for p in card.pulses)],
            "signals": [signal_view(signal, user, card, current) for signal in signals if signal.status != "resolved"],
            "resolved_signals": [signal_view(signal, user, card, current) for signal in signals if signal.status == "resolved"][:8],
            "waiting": [signal_view(signal, user, card, current) for signal in signals if signal.status == "waiting_recheck"],
            "events": [
                {"at": event.created_at.isoformat(), "actor": event.actor_name, "text": event.text}
                for event in events
            ],
            "permissions": {
                "edit_items": edit_items,
                "assign_mentor": manage and editable(card),
                "edit_schedule": manage and editable(card),
                "admission": edit_items and card.track.code in FLOOR_TRACKS and day_reached(card, 14, current),
                "day30": manage and card.probation_days >= 30 and day_reached(card, 30, current),
                "day60": edit_items and card.probation_days > 60 and day_reached(card, 60, current),
                "decision": manage and unlocked,
                "decision_hint": _decision_hint(card, unlocked),
            },
        }
    )
    # waiting signals are also in signals if I included status != resolved. waiting_recheck != resolved.
    # I duplicated waiting inside signals. Filter signals to open only, waiting separate.
    data["signals"] = [row for row in data["signals"] if row["status"] == "open"]
    return data


def _pulse_view(card: Card, day: int, edit_items: bool, current: date) -> dict:
    pulse = next(row for row in card.pulses if row.day_number == day)
    due = card.start_date.fromordinal(card.start_date.toordinal() + day - 1)
    return {
        "day": day,
        "due_date": due.isoformat(),
        "q1": pulse.q1,
        "q2": pulse.q2,
        "q3": pulse.q3,
        "comment": pulse.comment,
        "recorded_at": _iso(pulse.recorded_at),
        "can_record": edit_items and current >= due,
    }


def _decision_hint(card: Card, unlocked: bool) -> str:
    if card.stage in ("closed", "dismissed"):
        return "Карточка закрыта."
    if unlocked:
        if card.probation_days <= 0:
            return "Испытание не устанавливалось. Подтвердите выход или расставание."
        return "Можно закрыть испытание: подтвердить, расстаться или перевести внутри точки."
    return f"Решение откроется {card.probation_end_date.strftime('%d.%m.%Y')}, в дату конца испытания. Раньше его открывает запуск расставания."


def user_public(user: User) -> dict:
    nav = ["queue", "cards", "summary", "guide"]
    if user.role == "hr":
        nav = ["queue", "cards", "new", "summary", "templates", "guide"]
    if user.role == "director":
        nav = ["summary", "queue", "cards", "guide"]
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "title": user.title,
        "location_name": user.location.name if user.location else None,
        "nav": nav,
    }
