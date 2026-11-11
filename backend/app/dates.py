"""Рабочие дни и окна контрольных точек. Праздники не учитываются, только суббота и воскресенье."""

from __future__ import annotations

from datetime import date, timedelta


def next_working_day(day: date) -> date:
    cursor = day + timedelta(days=1)
    while cursor.weekday() >= 5:
        cursor += timedelta(days=1)
    return cursor


def shift_working_days(day: date, steps: int) -> date:
    step = 1 if steps >= 0 else -1
    left = abs(steps)
    cursor = day
    while left:
        cursor += timedelta(days=step)
        if cursor.weekday() < 5:
            left -= 1
    return cursor


def checkpoint_due(start: date, day_number: int) -> date:
    return start + timedelta(days=day_number - 1)


def window_status(due: date, today: date) -> str:
    grace = next_working_day(due)
    if today > grace:
        return "overdue"
    if today >= due:
        return "open"
    return "future"


def find_start(
    today: date,
    *,
    overdue: int | None = None,
    open_day: int | None = None,
    future: int | None = None,
) -> date:
    for delta in range(0, 240):
        start = today - timedelta(days=delta)
        if start.weekday() >= 5:
            continue

        def status(day_number: int) -> str:
            return window_status(checkpoint_due(start, day_number), today)

        if overdue is not None and status(overdue) != "overdue":
            continue
        if open_day is not None and status(open_day) != "open":
            continue
        if future is not None and status(future) != "future":
            continue
        return start
    raise RuntimeError(
        f"Не нашёл дату выхода: overdue={overdue} open={open_day} future={future} today={today.isoformat()}"
    )


def on_working_day(day: date) -> date:
    cursor = day
    while cursor.weekday() >= 5:
        cursor -= timedelta(days=1)
    return cursor
