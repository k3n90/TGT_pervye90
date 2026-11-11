"""Вымышленные сотрудники. Даты считаются от сегодняшнего дня, чтобы очередь была красной в любой день недели."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.content import BASELINE_PLAN, TRACKS, USERS, assert_track_limits
from app.dates import find_start, on_working_day
from app.logic import add_event, apply_mark, copy_structure, now, probation_end, sync_card
from app.models import (
    BaselinePerson,
    Card,
    ChecklistTemplate,
    Department,
    Location,
    Position,
    Track,
    User,
    UserDepartment,
)
from app.security import hash_password


def seed_if_empty(db: Session) -> None:
    if db.query(User).count():
        return
    seed_all(db)


def seed_all(db: Session) -> None:
    assert_track_limits()
    departments = _departments(db)
    tracks, positions, locations = _tracks(db, departments)
    users = _users(db, locations, departments)
    _templates(db, tracks, positions)
    _baseline(db, departments)
    _stories(db, tracks, positions, locations, users)
    db.flush()


def _departments(db: Session) -> dict[str, Department]:
    found = {}
    for track in TRACKS:
        department = Department(code=track["code"], name=track["department"])
        db.add(department)
        found[track["code"]] = department
    db.flush()
    return found


def _tracks(db: Session, departments: dict[str, Department]):
    tracks: dict[str, Track] = {}
    positions: dict[str, Position] = {}
    locations: dict[str, Location] = {}
    for spec in TRACKS:
        track = Track(
            code=spec["code"],
            name=spec["name"],
            department_id=departments[spec["code"]].id,
            independence_day=spec["independence_day"],
        )
        db.add(track)
        db.flush()
        tracks[spec["code"]] = track
        location = Location(department_id=departments[spec["code"]].id, name=spec["location"])
        db.add(location)
        db.flush()
        locations[spec["code"]] = location
        for code, name in spec["positions"]:
            position = Position(track_id=track.id, code=code, name=name)
            db.add(position)
            positions[code] = position
    db.flush()
    return tracks, positions, locations


def _users(db: Session, locations: dict[str, Location], departments: dict[str, Department]) -> dict[str, User]:
    found = {}
    password_hash = hash_password("demo")
    for username, full_name, role, track_code, title, dept_codes in USERS:
        user = User(
            username=username,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            title=title,
            location_id=locations[track_code].id if track_code and role != "director" else None,
        )
        db.add(user)
        db.flush()
        for code in dept_codes:
            db.add(UserDepartment(user_id=user.id, department_id=departments[code].id))
        found[username] = user
    db.flush()
    return found


def _templates(db: Session, tracks: dict[str, Track], positions: dict[str, Position]) -> None:
    for spec in TRACKS:
        for index, (code, day, critical, include, position_code, title) in enumerate(spec["items"], start=1):
            db.add(
                ChecklistTemplate(
                    track_id=tracks[spec["code"]].id,
                    code=code,
                    checkpoint_day=day,
                    is_critical=critical,
                    include_mode=include,
                    position_code=position_code,
                    title=title,
                    sort_order=index,
                    is_active=True,
                )
            )
    db.flush()


def _baseline(db: Session, departments: dict[str, Department]) -> None:
    rng = random.Random(90)
    current = date.today()
    for code, (hires, _leavers, short, under30, long_count) in BASELINE_PLAN.items():
        department_id = departments[code].id
        short_under = under30
        short_rest = short - under30
        stay = hires - short - long_count
        band: list[tuple[str, int, int]] = (
            [("under30", 6, 27)] * short_under
            + [("short", 31, 88)] * short_rest
            + [("long", 130, 260)] * long_count
            + [("stay", 0, 0)] * stay
        )
        for kind, low, high in band:
            if kind == "stay":
                started = current - timedelta(days=rng.randint(140, 360))
                left = None
            else:
                tenure = rng.randint(low, high)
                # Старт не моложе 120 дней, чтобы 30-й и 90-й день уже можно было посчитать.
                started = current - timedelta(days=max(120, tenure + 15) + rng.randint(0, 80))
                left = started + timedelta(days=tenure)
            db.add(BaselinePerson(department_id=department_id, started_on=started, left_on=left))


def _stories(db, tracks, positions, locations, users) -> None:
    current = date.today()
    neglected = current - timedelta(days=4)

    def person(**kwargs):
        return _make(db, users, positions, locations, **kwargs)

    person(
        name="Никита Бондарь",
        position="picker",
        track="warehouse",
        start=_future_working(current, 1),
        mentor=None,
        manager="denis",
        schedule="09:00–18:00, склад, первая смена со старшим.",
        source="Работный сайт",
        event="Заявка на выход принята. Наставник не назван.",
        opened_on=neglected,
        expect_red={"no_mentor"},
    )

    start_day1 = find_start(current, overdue=1, future=7)
    person(
        name="Артём Савич",
        position="picker",
        track="warehouse",
        start=start_day1,
        mentor="pavel",
        mentor_on=datetime.combine(start_day1 + timedelta(days=1), time(11, 0)),
        manager="denis",
        schedule="09:00–18:00, комплектация розницы.",
        source="Пришёл сам",
        event="Наставник назначен на следующий день после выхода. Отметки первой смены нет.",
        opened_on=neglected,
        expect_red={"missed_day_1"},
    )
    person(
        name="Егор Литвин",
        position="picker",
        track="warehouse",
        start=find_start(current, overdue=7, future=14),
        mentor="pavel",
        manager="denis",
        schedule="11:00–20:00, вечерняя волна.",
        source="Работный сайт",
        marks={"through": 7},
        pulse7=("yes", "yes", "no", "Вечерние смены не совпали с тем, что обсуждали при выходе."),
        event="После седьмой смены Егор сказал, что оставаться не хочет.",
        opened_on=neglected,
        expect_red={"pulse_no"},
    )
    person(
        name="Марина Крук",
        position="picker",
        track="warehouse",
        start=find_start(current, overdue=14, future=30),
        mentor="pavel",
        manager="denis",
        schedule="09:00–18:00, обычная волна.",
        source="Рекомендация сотрудника",
        marks={"through": 14, "not_yet": {"wh_wave": 2}},
        pulse7=("yes", "yes", "yes", ""),
        event="Критический пункт волны отмечен «нет» второй раз. Допуска нет.",
        opened_on=neglected,
        expect_red={"critical_twice", "no_admission"},
    )
    person(
        name="Павел Емец",
        position="storekeeper",
        track="warehouse",
        start=find_start(current, overdue=30, future=60),
        mentor="pavel",
        manager="denis",
        schedule="08:00–17:00, приёмка.",
        source="Работный сайт",
        marks={"through": 14},
        admission=("yes", "", True),
        pulse7=("yes", "yes", "yes", ""),
        event="Первые две недели закрыты. Точку 30-го дня руководитель не закрыл.",
        opened_on=neglected,
        expect_red={"missed_day_30"},
    )
    person(
        name="Ольга Верба",
        position="picker",
        track="warehouse",
        start=find_start(current, overdue=90),
        mentor="pavel",
        manager="denis",
        schedule="09:00–18:00.",
        source="Рекомендация сотрудника",
        marks={"through": 14},
        admission=("yes", "", True),
        pulse7=("yes", "yes", "yes", ""),
        pulse30=("yes", "yes", "yes", ""),
        day30=("independent", "", None),
        day60=(True, "Откатов нет."),
        event="Точки 30 и 60 закрыты. Решение по испытанию пустое.",
        opened_on=neglected,
        expect_red={"missed_final"},
    )
    person(
        name="Илья Гордеев",
        position="picker",
        track="warehouse",
        start=find_start(current, overdue=1, future=7),
        mentor="pavel",
        manager="denis",
        schedule="09:00–18:00, рядом с Павлом.",
        source="Рекомендация сотрудника",
        marks={"through": 1},
        event="Первая смена отмечена, седьмой день ещё впереди.",
        expect_red=set(),
    )
    person(
        name="Тарас Мельник",
        position="picker",
        track="warehouse",
        start=find_start(current, overdue=1, future=7),
        mentor="pavel",
        manager="denis",
        schedule="09:00–18:00, общий склад со техникой RAGEX.",
        source="Пришёл сам",
        shared=True,
        marks={"through": 1, "skip": {"wh_ragex"}},
        event="Пункт про гарантийный стикер RAGEX не отмечен, первая смена не закрыта.",
        opened_on=neglected,
        expect_red={"missed_day_1"},
    )
    person(
        name="Алина Шевчук",
        position="seller",
        track="retail",
        start=find_start(current, open_day=1, future=7),
        mentor="irina",
        manager="marina",
        schedule="15:00–21:00, зал пом. 411, рядом с Ириной.",
        source="Объявление у входа",
        event="Первая смена идёт сейчас. Отметки ещё можно поставить в срок.",
        expect_red=set(),
    )
    person(
        name="Катя Новик",
        position="seller",
        track="retail",
        start=find_start(current, overdue=1, future=7),
        mentor="irina",
        manager="marina",
        schedule="09:00–18:00, зал.",
        source="Рекомендация сотрудника",
        marks={"through": 1},
        event="Первый день закрыт без красных пунктов.",
        expect_red=set(),
    )
    person(
        name="Дима Олех",
        position="seller",
        track="retail",
        start=find_start(current, overdue=14, future=30),
        mentor="irina",
        manager="marina",
        schedule="12:00–21:00, в том числе воскресенье.",
        source="Работный сайт",
        marks={"through": 14},
        admission=("caveat", "Путает карты рассрочки, на кассе пока рядом со старшим.", False),
        pulse7=("yes", "mid", "yes", "Путаюсь, какая рассрочка чем отличается."),
        event="Допуск с оговоркой. Жёлтый сигнал для планёрки, в очередь кадров не идёт.",
        opened_on=current - timedelta(days=3),
        expect_red=set(),
        expect_yellow={"pulse_mid", "admission_caveat"},
    )
    person(
        name="Аня Петрович",
        position="shift_lead",
        track="retail",
        start=find_start(current, overdue=30, future=60),
        mentor="irina",
        manager="marina",
        schedule="Вечерние пики, зал пом. 411.",
        source="Рекомендация сотрудника",
        marks={"through": 30},
        admission=("yes", "", True),
        pulse7=("yes", "yes", "yes", ""),
        pulse30=("yes", "yes", "yes", ""),
        day30=("still_with_mentor", "Не держит вечернюю смену одна, на пике зовёт старшего.", current + timedelta(days=5)),
        event="30-й день: ещё с наставником, повторная проверка назначена.",
        expect_red=set(),
        expect_yellow={"still_with_mentor"},
    )
    person(
        name="Гена Быков",
        position="seller",
        track="retail",
        start=on_working_day(current - timedelta(days=12)),
        mentor="irina",
        manager="marina",
        schedule="15:00–21:00.",
        source="Работный сайт",
        marks={"through": 1},
        dismissed=current,
        decision=("separate", "График вечера не подошёл, расстались на второй неделе.", None),
        event="Увольнение внесено в карточку вместе с решением, а не только приказом.",
        expect_red=set(),
    )
    person(
        name="Лена Махнач",
        position="wholesale_manager",
        track="wholesale",
        start=find_start(current, overdue=1, future=7),
        mentor="natalia",
        manager="viktor",
        schedule="09:00–18:00, ПВЗ пом. 417.",
        source="Рекомендация сотрудника",
        marks={"through": 1},
        event="Первый день опта закрыт. Самостоятельный заказ — точка 30-го дня, не 14-го.",
        expect_red=set(),
    )
    person(
        name="Вика Сазонова",
        position="ragex_specialist",
        track="ragex",
        start=find_start(current, overdue=7, future=14),
        mentor="kirill",
        manager="roman",
        schedule="09:00–18:00, карточки и гарантия.",
        source="Работный сайт",
        marks={"through": 7},
        pulse7=("no", "mid", "yes", "Не уверена, когда гарантия 12 месяцев, а когда 24."),
        event="На вопросе про ожидания ответ «нет».",
        opened_on=neglected,
        expect_red={"pulse_no"},
    )
    person(
        name="Сергей Ким",
        position="office_specialist",
        track="office",
        start=find_start(current, overdue=14, future=30),
        mentor="elena",
        manager="tatiana",
        schedule="09:00–18:00, офис пом. 427.",
        source="Рекомендация сотрудника",
        marks={"through": 14},
        pulse7=("yes", "yes", "yes", ""),
        event="Доступы открыты, типовую задачу закрыл с одной правкой.",
        expect_red=set(),
    )
    person(
        name="Юля Адамович",
        position="picker",
        track="warehouse",
        start=on_working_day(current - timedelta(days=140)),
        mentor="pavel",
        manager="denis",
        schedule="09:00–18:00.",
        source="Рекомендация сотрудника",
        marks={"through": 14},
        admission=("yes", "", True),
        pulse7=("yes", "yes", "yes", ""),
        pulse30=("yes", "yes", "yes", ""),
        day30=("independent", "", None),
        day60=(True, "Смена устойчивая."),
        decision=("confirm", "Смена сама, критических ошибок за испытание нет.", None),
        event="Испытание подтверждено по отметкам, не по памяти руководителя.",
        expect_red=set(),
    )
    person(
        name="Рома Гук",
        position="picker",
        track="warehouse",
        start=on_working_day(current - timedelta(days=80)),
        mentor="pavel",
        manager="denis",
        schedule="09:00–18:00.",
        source="Пришёл сам",
        marks={"through": 14},
        admission=("yes", "", True),
        pulse7=("yes", "yes", "yes", ""),
        pulse30=("yes", "yes", "yes", ""),
        day30=("independent", "", None),
        dismissed=current - timedelta(days=30),
        decision=("separate", "Ушёл сам на 40-й день, решение в карточке есть.", None),
        event="Допуск был вовремя. Уход случился после 30-го дня и до конца испытания.",
        expect_red=set(),
    )


def _future_working(current: date, steps: int) -> date:
    from app.dates import shift_working_days

    return shift_working_days(current, steps)


def _make(
    db: Session,
    users: dict[str, User],
    positions: dict[str, Position],
    locations: dict[str, Location],
    *,
    name: str,
    position: str,
    track: str,
    start: date,
    mentor: str | None,
    manager: str,
    schedule: str,
    source: str,
    event: str,
    marks: dict | None = None,
    pulse7: tuple | None = None,
    pulse30: tuple | None = None,
    admission: tuple | None = None,
    day30: tuple | None = None,
    day60: tuple | None = None,
    decision: tuple | None = None,
    dismissed: date | None = None,
    shared: bool = False,
    mentor_on: datetime | None = None,
    opened_on: date | None = None,
    expect_red: set[str] | None = None,
    expect_yellow: set[str] | None = None,
) -> Card:
    position_row = positions[position]
    card = Card(
        full_name=name,
        position_id=position_row.id,
        track_id=position_row.track_id,
        department_id=locations[track].department_id,
        location_id=locations[track].id,
        start_date=start,
        probation_days=90,
        probation_end_date=probation_end(start, 90),
        first_shift_schedule=schedule,
        mentor_id=users[mentor].id if mentor else None,
        mentor_assigned_at=mentor_on
        or (datetime.combine(start - timedelta(days=2), time(10, 0)) if mentor else None),
        manager_id=users[manager].id,
        hire_source=source,
        shared_warehouse=shared,
        created_at=datetime.combine(start, time(9, 0)),
        admission="none",
    )
    db.add(card)
    db.flush()
    db.refresh(card)
    copy_structure(db, card)
    if marks:
        _apply_marks(card, marks)
    if admission:
        value, note, on_due = admission
        card.admission = value
        card.admission_note = note
        if value != "none":
            card.admission_date = card.start_date + timedelta(days=13) if on_due else date.today()
    if pulse7:
        _fill_pulse(card, 7, pulse7)
    if pulse30:
        _fill_pulse(card, 30, pulse30)
    if day30:
        choice, reason, recheck = day30
        card.day30_choice = choice
        card.day30_reason = reason or ""
        card.day30_recheck_date = recheck
    if day60:
        stable, note = day60
        card.day60_stable = stable
        card.day60_note = note
    if decision:
        kind, comment, _transfer = decision
        card.probation_decision = kind
        card.probation_decision_comment = comment
        card.probation_decision_date = dismissed or card.probation_end_date
    if dismissed:
        card.dismissed_date = dismissed
        card.separation_started = True
    add_event(
        db,
        card,
        "Ольга Сеницкая",
        event,
        when=datetime.combine(start, time(9, 30)),
    )
    sync_card(db, card, stamp_on_due=True, opened_on=opened_on, silent=True)
    db.flush()
    db.expire(card, ["signals", "checkpoints", "items", "pulses"])
    if expect_red is not None:
        got = {signal.code for signal in card.signals if signal.status == "open" and signal.severity == "red"}
        if got != expect_red:
            raise RuntimeError(f"{name}: красные {sorted(got)} вместо {sorted(expect_red)} (выход {start.isoformat()})")
    if expect_yellow is not None:
        got = {signal.code for signal in card.signals if signal.status == "open" and signal.severity == "yellow"}
        if got != expect_yellow:
            raise RuntimeError(f"{name}: жёлтые {sorted(got)} вместо {sorted(expect_yellow)} (выход {start.isoformat()})")
    return card


def _apply_marks(card: Card, marks: dict) -> None:
    through = marks.get("through", 0)
    not_yet = marks.get("not_yet", {})
    skip = marks.get("skip", set())
    for item in card.items:
        if item.code in skip:
            continue
        if item.checkpoint_day > through:
            continue
        if item.code in not_yet:
            for _ in range(not_yet[item.code]):
                apply_mark(item, "not_yet")
        else:
            apply_mark(item, "yes")


def _fill_pulse(card: Card, day: int, payload: tuple) -> None:
    q1, q2, q3, comment = payload
    pulse = next(row for row in card.pulses if row.day_number == day)
    pulse.q1, pulse.q2, pulse.q3 = q1, q2, q3
    pulse.comment = comment
    pulse.recorded_at = datetime.combine(card.start_date + timedelta(days=day - 1), time(19, 0))
