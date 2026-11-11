from __future__ import annotations

from datetime import date
from typing import Optional

from app.content import STAGE_LABELS
from app.dates import checkpoint_due, next_working_day, window_status
from app.logic import FLOOR_TRACKS, today
from app.models import BaselinePerson, Card, Department


def build_summary(cards: list[Card], people: list[BaselinePerson], departments: list[Department]) -> dict:
    current = today()
    month_start = current.replace(day=1)
    dept_name = {department.id: department.name for department in departments}

    def in_month(value: Optional[date]) -> bool:
        return bool(value and value >= month_start and value <= current)

    operations_rows = []
    for department in departments:
        own = [card for card in cards if card.department_id == department.id]
        left = [card for card in own if card.dismissed_date and in_month(card.dismissed_date)]
        operations_rows.append(
            {
                "name": department.name,
                "starts": sum(1 for card in own if in_month(card.start_date)),
                "open_reds": _open_reds(own),
                "left_under_30": sum(1 for card in left if _tenure(card) < 30),
                "left_under_90": sum(1 for card in left if _tenure(card) < 90),
                "admitted": _admitted_ratio(own, current),
            }
        )

    open_red_signals = [signal for card in cards for signal in card.signals if signal.status == "open" and signal.severity == "red"]
    closed_points = 0
    for card in cards:
        for checkpoint in card.checkpoints:
            if checkpoint.completed_at and in_month(checkpoint.completed_at.date()):
                closed_points += 1

    left_month = [card for card in cards if card.dismissed_date and in_month(card.dismissed_date)]
    pilot = _pilot(cards, current)
    baseline = _baseline(people, departments, current)

    return {
        "today": current.isoformat(),
        "month_label": _month_label(current),
        "scope_note": "Цифры кабинета считаются по вымышленным карточкам. База за 12 месяцев — отдельная демонстрационная выборка, она не смешана с карточками.",
        "operations": {
            "starts": sum(row["starts"] for row in operations_rows),
            "open_reds": len(open_red_signals),
            "open_reds_overdue": sum(1 for signal in open_red_signals if signal.due_at and current > signal.due_at),
            "checkpoints_closed": closed_points,
            "left_under_30": sum(1 for card in left_month if _tenure(card) < 30),
            "left_under_90": sum(1 for card in left_month if _tenure(card) < 90),
            "by_department": operations_rows,
        },
        "pilot": pilot,
        "baseline": baseline,
        "stage_labels": STAGE_LABELS,
        "department_names": list(dept_name.values()),
    }


def _tenure(card: Card) -> int:
    if not card.dismissed_date:
        return 0
    return (card.dismissed_date - card.start_date).days


def _open_reds(cards: list[Card]) -> int:
    return sum(1 for card in cards for signal in card.signals if signal.status == "open" and signal.severity == "red")


def _admitted_ratio(cards: list[Card], current: date) -> str:
    den = 0
    num = 0
    for card in cards:
        if card.track.code not in FLOOR_TRACKS:
            continue
        due = checkpoint_due(card.start_date, 14)
        if card.dismissed_date and card.dismissed_date < due:
            continue
        if window_status(due, current) != "overdue":
            continue
        den += 1
        if card.admission == "yes" and card.admission_date and card.admission_date <= due:
            num += 1
    if den == 0:
        return "—"
    return f"{num} из {den}"


def _pilot(cards: list[Card], current: date) -> dict:
    started = [card for card in cards if card.start_date <= current]
    mentor_num = sum(
        1
        for card in started
        if card.mentor_assigned_at and card.mentor_assigned_at.date() <= card.start_date
    )
    day_num, day_den = _day_pair(cards, current)
    ind_num, ind_den = _independent(cards, current)
    red_num, red_den = _red_sla(cards, current)
    ended = [
        card
        for card in cards
        if card.probation_end_date <= current or card.dismissed_date is not None
    ]
    decided = sum(1 for card in ended if card.probation_decision)
    return {
        "mentor_before_day1": _ratio(mentor_num, len(started), "Выходы, у которых наставник назван до первого дня."),
        "day1_and_14_on_time": _ratio(
            day_num,
            day_den,
            "Склад и розница, у которых и 1-й, и 14-й день закрыты до конца следующего рабочего дня. В знаменателе только те, у кого срок 14-го дня уже прошёл.",
        ),
        "independent_by_14": _ratio(
            ind_num,
            ind_den,
            "Склад и розница с допуском «работает сам» не позже 14-го дня. Оговорка сюда не входит.",
        ),
        "reds_in_two_days": _ratio(
            red_num,
            red_den,
            "Красные сигналы, разобранные за два рабочих дня. Висящие дольше срока попадают в знаменатель как неразобранные.",
        ),
        "decisions_recorded": _ratio(
            decided,
            len(ended),
            "Карточки, у которых испытание закончилось или человек уволен, и решение записано в карточке, а не только в приказе.",
        ),
    }


def _ratio(num: int, den: int, hint: str) -> dict:
    return {"num": num, "den": den, "hint": hint}


def _checkpoint(card: Card, day: int):
    return next((row for row in card.checkpoints if row.day_number == day), None)


def _on_time(checkpoint) -> bool:
    if checkpoint is None or checkpoint.completed_at is None:
        return False
    return checkpoint.completed_at.date() <= next_working_day(checkpoint.due_date)


def _day_pair(cards: list[Card], current: date) -> tuple[int, int]:
    num = den = 0
    for card in cards:
        if card.track.code not in FLOOR_TRACKS:
            continue
        day14 = _checkpoint(card, 14)
        if day14 is None:
            continue
        if card.dismissed_date and card.dismissed_date < day14.due_date:
            continue
        if window_status(day14.due_date, current) != "overdue":
            continue
        den += 1
        if _on_time(_checkpoint(card, 1)) and _on_time(day14):
            num += 1
    return num, den


def _independent(cards: list[Card], current: date) -> tuple[int, int]:
    num = den = 0
    for card in cards:
        if card.track.code not in FLOOR_TRACKS:
            continue
        due = checkpoint_due(card.start_date, 14)
        if card.dismissed_date and card.dismissed_date < due:
            continue
        if window_status(due, current) != "overdue":
            continue
        den += 1
        if card.admission == "yes" and card.admission_date and card.admission_date <= due:
            num += 1
    return num, den


def _red_sla(cards: list[Card], current: date) -> tuple[int, int]:
    num = den = 0
    for card in cards:
        for signal in card.signals:
            if signal.severity != "red":
                continue
            if signal.status == "resolved" and signal.resolution in ("fixed", "recheck", "separation"):
                den += 1
                if signal.resolved_at and signal.due_at and signal.resolved_at.date() <= signal.due_at:
                    num += 1
            elif signal.status == "open" and signal.due_at and current > signal.due_at:
                den += 1
    return num, den


def _baseline(people: list[BaselinePerson], departments: list[Department], current: date) -> dict:
    def pack(rows: list[BaselinePerson]) -> dict:
        hired = len(rows)
        leavers = [row for row in rows if row.left_on]
        def tenure(row: BaselinePerson) -> int:
            assert row.left_on is not None
            return (row.left_on - row.started_on).days

        under30 = sum(1 for row in leavers if tenure(row) < 30)
        under90 = sum(1 for row in leavers if tenure(row) < 90)
        cohort90 = [row for row in rows if row.started_on <= current.fromordinal(current.toordinal() - 90)]
        survived90 = [
            row
            for row in cohort90
            if row.left_on is None or (row.left_on - row.started_on).days >= 90
        ]
        cohort30 = [row for row in rows if row.started_on <= current.fromordinal(current.toordinal() - 30)]
        survived30 = [
            row
            for row in cohort30
            if row.left_on is None or (row.left_on - row.started_on).days >= 30
        ]
        return {
            "hired": hired,
            "left": len(leavers),
            "left_under_30": under30,
            "left_under_90": under90,
            "share_leavers_under_90": (under90 / len(leavers)) if leavers else None,
            "survival_30": (len(survived30) / len(cohort30)) if cohort30 else None,
            "survival_90": (len(survived90) / len(cohort90)) if cohort90 else None,
        }

    by_department = []
    for department in departments:
        own = [row for row in people if row.department_id == department.id]
        packed = pack(own)
        packed["name"] = department.name
        by_department.append(packed)
    total = pack(people)
    total["by_department"] = by_department
    total["caption"] = (
        "Так выглядит замер за 12 месяцев: среди уволившихся около трети не доработали до 90 дней. "
        "Доля тех, кто ещё работал на 90-й день, — другая дробь, рядом."
    )
    return total


def _month_label(current: date) -> str:
    months = [
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",
    ]
    return f"{months[current.month - 1]} {current.year}"
