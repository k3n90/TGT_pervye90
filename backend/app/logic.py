"""Стадии карточки, закрытие точек и очередь сигналов."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.content import QUESTIONS
from app.dates import checkpoint_due, next_working_day, shift_working_days, window_status
from app.models import Card, CardItem, Checkpoint, ChecklistTemplate, Event, Pulse, Signal

FLOOR_TRACKS = {"warehouse", "retail"}
JUDGMENT_CODES = {"pulse_no", "critical_twice", "role_unfit", "recheck_missed"}
QUESTION_TEXT = dict(QUESTIONS)


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def today() -> date:
    return date.today()


def probation_end(start: date, probation_days: int) -> date:
    if probation_days <= 0:
        return checkpoint_due(start, 14)
    return checkpoint_due(start, probation_days)


def checkpoint_plan(probation_days: int) -> list[int]:
    if probation_days <= 0:
        return [1, 7, 14]
    days = [day for day in (1, 7, 14, 30, 60) if day < probation_days]
    if probation_days not in days:
        days.append(probation_days)
    return days


def pulse_plan(probation_days: int) -> list[int]:
    days = [7]
    if probation_days >= 30:
        days.append(30)
    return days


def item_due(card: Card, day_number: int) -> date:
    return checkpoint_due(card.start_date, day_number)


def day_reached(card: Card, day_number: int, on: date | None = None) -> bool:
    return (on or today()) >= item_due(card, day_number)


def update_stage(card: Card, on: date | None = None) -> None:
    current = on or today()
    if card.dismissed_date:
        card.stage = "dismissed"
        return
    if card.probation_decision in ("confirm", "transfer"):
        card.stage = "closed"
        return
    if current < card.start_date:
        card.stage = "waiting"
    elif current < card.start_date + timedelta(days=7):
        card.stage = "first_week"
    elif current < card.start_date + timedelta(days=30):
        card.stage = "until_30"
    else:
        card.stage = "until_end"


def pulse_on(card: Card, day_number: int) -> Pulse | None:
    return next((pulse for pulse in card.pulses if pulse.day_number == day_number), None)


def pulse_filled(card: Card, day_number: int) -> bool:
    pulse = pulse_on(card, day_number)
    return bool(pulse and pulse.q1 and pulse.q2 and pulse.q3)


def items_marked_through(card: Card, day_number: int) -> bool:
    relevant = [item for item in card.items if item.checkpoint_day <= day_number]
    return all(item.mark for item in relevant)


def checkpoint_met(card: Card, checkpoint: Checkpoint) -> bool:
    day = checkpoint.day_number
    if checkpoint.is_final:
        if card.probation_days <= 0:
            base = card.probation_decision is not None and items_marked_through(card, day)
            if card.track.code in FLOOR_TRACKS:
                return base and card.admission != "none"
            return base
        return card.probation_decision is not None
    if day == 1:
        return items_marked_through(card, 1)
    if day == 7:
        return items_marked_through(card, 7) and pulse_filled(card, 7)
    if day == 14:
        if card.track.code in FLOOR_TRACKS:
            return items_marked_through(card, 14) and card.admission != "none"
        return items_marked_through(card, 14)
    if day == 30:
        return items_marked_through(card, 30) and pulse_filled(card, 30) and card.day30_choice is not None
    if day == 60:
        return card.day60_stable is not None
    return items_marked_through(card, day)


def refresh_checkpoints(card: Card, *, stamp_on_due: bool) -> None:
    moment = now()
    for checkpoint in card.checkpoints:
        if checkpoint_met(card, checkpoint):
            if checkpoint.completed_at is None:
                if stamp_on_due and checkpoint.due_date <= today():
                    checkpoint.completed_at = datetime.combine(checkpoint.due_date, time(18, 0))
                else:
                    checkpoint.completed_at = moment
        elif checkpoint.completed_at is not None and card.stage not in ("closed", "dismissed"):
            checkpoint.completed_at = None


def add_event(db: Session, card: Card, actor: str, text: str, when: datetime | None = None) -> None:
    event = Event(card_id=card.id, created_at=when or now(), actor_name=actor, text=text)
    db.add(event)
    card.events.append(event)


def _owner_id(card: Card, prefer: str) -> int | None:
    if prefer == "mentor" and card.mentor_id:
        return card.mentor_id
    return card.manager_id


def _fmt(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def desired_signals(card: Card, on: date | None = None) -> dict[str, dict]:
    current = on or today()
    if card.stage in ("closed", "dismissed"):
        return {}

    found: dict[str, dict] = {}

    def put(code: str, severity: str, title: str, detail: str, prefer: str, fingerprint: str) -> None:
        found[code] = {
            "severity": severity,
            "title": title,
            "detail": detail,
            "owner_id": _owner_id(card, prefer),
            "fingerprint": fingerprint,
        }

    if card.mentor_id is None and current >= shift_working_days(card.start_date, -2):
        put(
            "no_mentor",
            "red",
            "Не назначен наставник",
            f"Выход {_fmt(card.start_date)}. Наставника нет за два рабочих дня до смены.",
            "manager",
            "no-mentor",
        )

    for checkpoint in card.checkpoints:
        if checkpoint_met(card, checkpoint):
            continue
        if window_status(checkpoint.due_date, current) != "overdue":
            continue
        if checkpoint.is_final:
            if card.separation_started:
                continue
            put(
                "missed_final",
                "red",
                "Нет решения по испытанию",
                f"Срок испытания закончился {_fmt(checkpoint.due_date)}, решения в карточке нет.",
                "manager",
                "missed-final",
            )
            continue
        if checkpoint.day_number == 14 and card.track.code in FLOOR_TRACKS and items_marked_through(card, 14):
            continue
        put(
            f"missed_day_{checkpoint.day_number}",
            "red",
            f"Нет отметки {checkpoint.day_number}-го дня",
            f"Точка была {_fmt(checkpoint.due_date)}, к следующему рабочему дню отметки нет.",
            "mentor" if checkpoint.day_number in (1, 7, 14, 60) else "manager",
            f"missed-{checkpoint.day_number}",
        )

    if (
        card.track.code in FLOOR_TRACKS
        and window_status(checkpoint_due(card.start_date, 14), current) == "overdue"
        and items_marked_through(card, 14)
        and card.admission == "none"
    ):
        put(
            "no_admission",
            "red",
            "Нет допуска к типовой операции",
            "14-й день прошёл. К типовой операции человека не допустили и оговорку не записали.",
            "mentor",
            "no-admission",
        )

    pulse7 = pulse_on(card, 7)
    if pulse7 and pulse7.q1:
        answers = {"q1": pulse7.q1, "q2": pulse7.q2, "q3": pulse7.q3}
        negatives = [QUESTION_TEXT[key] for key, value in answers.items() if value == "no"]
        mids = [QUESTION_TEXT[key] for key, value in answers.items() if value == "mid"]
        fingerprint = f"{pulse7.q1}|{pulse7.q2}|{pulse7.q3}|{pulse7.comment or ''}"
        if negatives:
            comment = f" Комментарий: {pulse7.comment}" if pulse7.comment else ""
            put(
                "pulse_no",
                "red",
                "Сотрудник ответил «нет»",
                f"7-й день, «нет» на: {', '.join(negatives)}.{comment}",
                "manager",
                fingerprint,
            )
        elif mids:
            put(
                "pulse_mid",
                "yellow",
                "Есть ответ «средне»",
                f"7-й день, «средне» на: {', '.join(mids)}.",
                "manager",
                fingerprint,
            )

    pulse30 = pulse_on(card, 30)
    if pulse30 and pulse30.q1:
        answers = {"q1": pulse30.q1, "q2": pulse30.q2, "q3": pulse30.q3}
        negatives = [QUESTION_TEXT[key] for key, value in answers.items() if value == "no"]
        mids = [QUESTION_TEXT[key] for key, value in answers.items() if value == "mid"]
        fingerprint = f"d30:{pulse30.q1}|{pulse30.q2}|{pulse30.q3}|{pulse30.comment or ''}"
        if negatives:
            comment = f" Комментарий: {pulse30.comment}" if pulse30.comment else ""
            put(
                "pulse_no",
                "red",
                "Сотрудник ответил «нет»",
                f"30-й день, «нет» на: {', '.join(negatives)}.{comment}",
                "manager",
                fingerprint,
            )
        elif mids and "pulse_no" not in found and "pulse_mid" not in found:
            put(
                "pulse_mid",
                "yellow",
                "Есть ответ «средне»",
                f"30-й день, «средне» на: {', '.join(mids)}.",
                "manager",
                fingerprint,
            )

    doubled = [item for item in card.items if item.is_critical and item.fail_count >= 2]
    if doubled:
        names = "; ".join(f"«{item.title}» — {item.fail_count} раз." for item in doubled)
        fingerprint = ",".join(f"{item.code}:{item.fail_count}" for item in doubled)
        put(
            "critical_twice",
            "red",
            "Критический пункт отмечен «нет» дважды",
            names,
            "manager",
            fingerprint,
        )

    if card.admission == "caveat":
        note = f" Оговорка: {card.admission_note}" if card.admission_note else ""
        put(
            "admission_caveat",
            "yellow",
            "Допуск с оговоркой",
            f"К типовой операции допущен с оговоркой.{note}",
            "manager",
            f"caveat:{card.admission_note}",
        )

    if card.day30_choice == "still_with_mentor" and card.day30_recheck_date:
        if card.day30_recheck_date < current:
            put(
                "recheck_missed",
                "red",
                "Повторная проверка не закрыта",
                f"На 30-й день оставили с наставником до {_fmt(card.day30_recheck_date)}. Дата прошла, решение не обновлено.",
                "manager",
                f"recheck:{card.day30_recheck_date.isoformat()}:{card.day30_reason}",
            )
        else:
            put(
                "still_with_mentor",
                "yellow",
                "Ещё с наставником",
                f"Причина: {card.day30_reason} Повторная проверка {_fmt(card.day30_recheck_date)}.",
                "manager",
                f"with-mentor:{card.day30_recheck_date.isoformat()}",
            )

    if card.day30_choice == "role_unfit" and not card.dismissed_date:
        put(
            "role_unfit",
            "red",
            "Роль не подходит",
            f"Руководитель записал: {card.day30_reason}",
            "manager",
            f"unfit:{card.day30_reason}",
        )

    if card.day60_stable is False:
        put(
            "day60_rollback",
            "yellow",
            "На 60-й день есть откат",
            card.day60_note or "Наставник отметил откат по смене.",
            "manager",
            f"rollback:{card.day60_note}",
        )

    return found


def sync_card(
    db: Session,
    card: Card,
    *,
    stamp_on_due: bool = False,
    opened_on: date | None = None,
    silent: bool = False,
    actor: str = "Система",
) -> None:
    update_stage(card)
    refresh_checkpoints(card, stamp_on_due=stamp_on_due)
    desired = desired_signals(card)
    current_rows = list(card.signals)

    for signal in current_rows:
        if signal.status not in ("open", "waiting_recheck"):
            continue
        spec = desired.get(signal.code)
        if spec is None:
            signal.status = "resolved"
            signal.resolution = "auto"
            signal.resolved_at = now()
            if not signal.comment:
                signal.comment = "Условие в карточке снято"
            if not silent:
                add_event(db, card, actor, f"Сигнал «{signal.title}» снят: условие больше не выполняется.")
            continue
        signal.detail = spec["detail"]
        signal.owner_id = spec["owner_id"]
        signal.severity = spec["severity"]
        if signal.status == "waiting_recheck" and signal.recheck_date and signal.recheck_date <= today():
            if signal.fingerprint == spec["fingerprint"]:
                signal.status = "open"
                signal.due_at = shift_working_days(today(), 2)
                if not silent:
                    add_event(db, card, actor, f"Повторная проверка наступила: «{signal.title}».")
            else:
                signal.status = "resolved"
                signal.resolution = "auto"
                signal.resolved_at = now()

    active_codes = {signal.code for signal in current_rows if signal.status in ("open", "waiting_recheck")}
    opened = opened_on or today()
    for code, spec in desired.items():
        if code in active_codes:
            continue
        suppressed = any(
            signal.code == code
            and signal.status == "resolved"
            and signal.resolution in ("fixed", "separation")
            and signal.fingerprint == spec["fingerprint"]
            for signal in current_rows
        )
        if suppressed:
            continue
        signal = Signal(
            card_id=card.id,
            code=code,
            severity=spec["severity"],
            title=spec["title"],
            detail=spec["detail"],
            owner_id=spec["owner_id"],
            status="open",
            fingerprint=spec["fingerprint"],
            opened_at=datetime.combine(opened, time(9, 0)),
            due_at=shift_working_days(opened, 2) if spec["severity"] == "red" else None,
        )
        db.add(signal)
        card.signals.append(signal)
        if not silent and spec["severity"] == "red":
            add_event(db, card, actor, f"В очереди красный сигнал: {spec['title']}.")


def copy_structure(db: Session, card: Card) -> None:
    templates = (
        db.query(ChecklistTemplate)
        .filter(ChecklistTemplate.track_id == card.track_id, ChecklistTemplate.is_active.is_(True))
        .order_by(ChecklistTemplate.sort_order)
        .all()
    )
    position_code = card.position.code
    for template in templates:
        take = False
        if template.include_mode == "always":
            take = True
        elif template.include_mode == "position":
            take = template.position_code == position_code
        elif template.include_mode == "shared_warehouse":
            take = card.shared_warehouse
        if not take:
            continue
        db.add(
            CardItem(
                card_id=card.id,
                code=template.code,
                checkpoint_day=template.checkpoint_day,
                is_critical=template.is_critical,
                title=template.title,
                sort_order=template.sort_order,
            )
        )
    plan = checkpoint_plan(card.probation_days)
    final_day = plan[-1]
    for day in plan:
        db.add(
            Checkpoint(
                card_id=card.id,
                day_number=day,
                due_date=checkpoint_due(card.start_date, day),
                is_final=day == final_day,
            )
        )
    for day in pulse_plan(card.probation_days):
        db.add(Pulse(card_id=card.id, day_number=day))
    db.flush()
    db.expire(card, ["items", "checkpoints", "pulses"])


def decision_unlocked(card: Card, on: date | None = None) -> bool:
    current = on or today()
    if card.stage in ("closed", "dismissed"):
        return False
    if card.separation_started or card.day30_choice == "role_unfit":
        return True
    return current >= card.probation_end_date


def can_view(user, card: Card) -> bool:
    if user.role == "hr":
        return True
    if user.role == "director":
        return card.department_id in {department.id for department in user.departments}
    if user.role == "manager":
        return card.manager_id == user.id or card.location_id == user.location_id
    if user.role == "mentor":
        return card.mentor_id == user.id
    return False


def editable(card: Card) -> bool:
    return card.stage not in ("closed", "dismissed")


def can_edit_items(user, card: Card) -> bool:
    if not editable(card):
        return False
    if user.role == "hr":
        return True
    if user.role == "manager" and (card.manager_id == user.id or card.location_id == user.location_id):
        return True
    return user.role == "mentor" and card.mentor_id == user.id


def can_manage(user, card: Card) -> bool:
    if not editable(card) and user.role != "hr":
        return False
    if user.role == "hr":
        return True
    return user.role == "manager" and (card.manager_id == user.id or card.location_id == user.location_id)


def apply_mark(item: CardItem, mark: str) -> None:
    if mark == "yes":
        item.mark = "yes"
        return
    if item.mark == "not_yet":
        item.fail_count += 1
    else:
        item.fail_count = max(item.fail_count, 1)
    item.mark = "not_yet"


def critical_count(card: Card) -> int:
    return sum(1 for item in card.items if item.is_critical)
