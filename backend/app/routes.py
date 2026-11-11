from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.content import HIRE_SOURCES, PROBATION_OPTIONS, QUESTIONS, ROLE_LABELS
from app.db import get_db
from app.deps import get_current_user, require_hr
from app.logic import (
    JUDGMENT_CODES,
    add_event,
    apply_mark,
    can_edit_items,
    can_manage,
    can_view,
    copy_structure,
    day_reached,
    decision_unlocked,
    desired_signals,
    editable,
    now,
    probation_end,
    sync_card,
    today,
)
from app.models import (
    Base,
    BaselinePerson,
    Card,
    ChecklistTemplate,
    Department,
    Location,
    Position,
    Signal,
    Track,
    User,
)
from app.schemas import (
    AdmissionIn,
    CardCreate,
    CardPatch,
    Day30In,
    Day60In,
    DecisionIn,
    LoginIn,
    MarkIn,
    PulseIn,
    ResolveIn,
    TemplateCreate,
    TemplatePatch,
)
from app.seed import seed_all
from app.serialize import card_brief, card_detail, signal_view, user_public
from app.summary import build_summary
from app.security import make_token, verify_password

router = APIRouter()


def _cards(db: Session):
    return db.query(Card).options(
        selectinload(Card.items),
        selectinload(Card.checkpoints),
        selectinload(Card.pulses),
        selectinload(Card.signals).selectinload(Signal.owner),
        selectinload(Card.events),
        selectinload(Card.mentor),
        joinedload(Card.manager),
        joinedload(Card.position),
        joinedload(Card.track),
        joinedload(Card.department),
        joinedload(Card.location),
    )


def _visible(db: Session, user: User):
    query = _cards(db)
    if user.role == "hr":
        return query
    if user.role == "director":
        ids = [department.id for department in user.departments]
        return query.filter(Card.department_id.in_(ids or [-1]))
    if user.role == "manager":
        return query.filter(or_(Card.manager_id == user.id, Card.location_id == user.location_id))
    if user.role == "mentor":
        return query.filter(Card.mentor_id == user.id)
    return query.filter(Card.id == -1)


def _one(db: Session, user: User, card_id: int) -> Card:
    card = _cards(db).filter(Card.id == card_id).one_or_none()
    if card is None or not can_view(user, card):
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    return card


def _sync_many(db: Session, cards: list[Card]) -> None:
    for card in cards:
        sync_card(db, card, silent=True)
    db.flush()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.query(Department).count()
    return {"ok": True}


@router.get("/auth/accounts")
def accounts(db: Session = Depends(get_db)):
    rows = db.query(User).options(joinedload(User.location)).order_by(User.id).all()
    return [
        {
            "username": row.username,
            "full_name": row.full_name,
            "role": row.role,
            "role_label": ROLE_LABELS.get(row.role, row.role),
            "title": row.title,
            "location_name": row.location.name if row.location else "Вся компания",
        }
        for row in rows
    ]


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(selectinload(User.departments), joinedload(User.location))
        .filter(User.username == payload.username)
        .one_or_none()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверное имя или пароль")
    return {"token": make_token(user.id), "user": user_public(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)


@router.get("/meta")
def meta(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    del user
    locations = db.query(Location).options(joinedload(Location.department)).all()
    positions = db.query(Position).options(joinedload(Position.track)).order_by(Position.id).all()
    people = db.query(User).filter(User.role.in_(["mentor", "manager"])).all()
    return {
        "locations": [
            {
                "id": location.id,
                "name": location.name,
                "department_code": location.department.code,
            }
            for location in locations
        ],
        "positions": [
            {
                "code": position.code,
                "name": position.name,
                "track_code": position.track.code,
                "track_name": position.track.name,
            }
            for position in positions
        ],
        "people": [
            {
                "id": person.id,
                "full_name": person.full_name,
                "role": person.role,
                "title": person.title,
                "location_id": person.location_id,
            }
            for person in people
        ],
        "sources": HIRE_SOURCES,
        "probation_options": PROBATION_OPTIONS,
        "questions": [{"code": code, "text": text} for code, text in QUESTIONS],
    }


@router.get("/cards")
def list_cards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cards = _visible(db, user).order_by(Card.start_date.desc(), Card.id.desc()).all()
    _sync_many(db, cards)
    db.commit()
    cards = _visible(db, user).order_by(Card.start_date.desc(), Card.id.desc()).all()
    return [card_brief(card) for card in cards]


@router.get("/cards/{card_id}")
def get_card(card_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    sync_card(db, card, silent=True)
    db.commit()
    card = _one(db, user, card_id)
    return card_detail(card, user)


@router.post("/cards")
def create_card(payload: CardCreate, db: Session = Depends(get_db), user: User = Depends(require_hr)):
    if payload.probation_days not in {0, 30, 60, 90}:
        raise HTTPException(status_code=400, detail="Срок испытания: 90, 60, 30 дней или без испытания")
    current = today()
    if payload.start_date < current - timedelta(days=160) or payload.start_date > current + timedelta(days=60):
        raise HTTPException(status_code=400, detail="Дата выхода слишком далеко от сегодняшнего дня")
    position = db.query(Position).options(joinedload(Position.track)).filter(Position.code == payload.position_code).one_or_none()
    if position is None:
        raise HTTPException(status_code=400, detail="Неизвестная должность")
    location = db.query(Location).filter(Location.id == payload.location_id).one_or_none()
    if location is None or location.department_id != position.track.department_id:
        raise HTTPException(status_code=400, detail="Точка не относится к этой должности")
    manager = db.get(User, payload.manager_id)
    if manager is None or manager.role != "manager" or manager.location_id != location.id:
        raise HTTPException(status_code=400, detail="Руководитель должен быть руководителем этой точки")
    mentor = None
    if payload.mentor_id:
        mentor = db.get(User, payload.mentor_id)
        if mentor is None or mentor.role != "mentor" or mentor.location_id != location.id:
            raise HTTPException(status_code=400, detail="Наставник должен быть наставником этой точки")
    if payload.shared_warehouse and position.track.code != "warehouse":
        raise HTTPException(status_code=400, detail="Общий склад с RAGEX отмечается только на складском треке")
    card = Card(
        full_name=payload.full_name.strip(),
        position_id=position.id,
        track_id=position.track_id,
        department_id=location.department_id,
        location_id=location.id,
        start_date=payload.start_date,
        probation_days=payload.probation_days,
        probation_end_date=probation_end(payload.start_date, payload.probation_days),
        first_shift_schedule=payload.first_shift_schedule.strip(),
        mentor_id=mentor.id if mentor else None,
        mentor_assigned_at=now() if mentor else None,
        manager_id=manager.id,
        hire_source=payload.hire_source.strip(),
        shared_warehouse=payload.shared_warehouse,
        created_at=now(),
        admission="none",
    )
    db.add(card)
    db.flush()
    db.refresh(card)
    copy_structure(db, card)
    add_event(db, card, user.full_name, "Выход зафиксирован. Карточка адаптации создана.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.patch("/cards/{card_id}")
def patch_card(card_id: int, payload: CardPatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    if not can_manage(user, card) or not editable(card):
        raise HTTPException(status_code=403, detail="Назначать наставника может руководитель точки или кадры")
    if payload.clear_mentor:
        card.mentor_id = None
        card.mentor_assigned_at = None
        add_event(db, card, user.full_name, "Наставник снят с карточки.")
    elif payload.mentor_id:
        mentor = db.get(User, payload.mentor_id)
        if mentor is None or mentor.role != "mentor" or mentor.location_id != card.location_id:
            raise HTTPException(status_code=400, detail="Наставник должен быть наставником этой точки")
        card.mentor_id = mentor.id
        card.mentor_assigned_at = now()
        add_event(db, card, user.full_name, f"Наставник: {mentor.full_name}.")
    if payload.first_shift_schedule is not None:
        if len(payload.first_shift_schedule.strip()) < 3:
            raise HTTPException(status_code=400, detail="Напишите график первой смены")
        card.first_shift_schedule = payload.first_shift_schedule.strip()
    if payload.hire_source is not None:
        card.hire_source = payload.hire_source.strip()
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/cards/{card_id}/items/{item_id}/mark")
def mark_item(
    card_id: int,
    item_id: int,
    payload: MarkIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _one(db, user, card_id)
    item = next((row for row in card.items if row.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Пункт не найден")
    if not can_edit_items(user, card):
        raise HTTPException(status_code=403, detail="Отмечать умения может наставник этой карточки, руководитель или кадры")
    if not editable(card):
        raise HTTPException(status_code=400, detail="Карточка закрыта")
    if not day_reached(card, item.checkpoint_day):
        raise HTTPException(status_code=400, detail="Эта точка ещё не наступила")
    apply_mark(item, payload.mark)
    word = "есть" if payload.mark == "yes" else "нет"
    add_event(db, card, user.full_name, f"«{item.title}»: {word}.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/cards/{card_id}/pulse")
def record_pulse(card_id: int, payload: PulseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    pulse = next((row for row in card.pulses if row.day_number == payload.day), None)
    if pulse is None:
        raise HTTPException(status_code=400, detail="На этом сроке испытания такого вопроса нет")
    if not can_edit_items(user, card) or not editable(card):
        raise HTTPException(status_code=403, detail="Ответы со слов сотрудника записывает наставник, руководитель или кадры")
    if not day_reached(card, payload.day):
        raise HTTPException(status_code=400, detail="Этот день ещё не наступил")
    pulse.q1, pulse.q2, pulse.q3 = payload.q1, payload.q2, payload.q3
    pulse.comment = payload.comment.strip()
    pulse.recorded_at = now()
    pulse.recorded_by_id = user.id
    add_event(db, card, user.full_name, f"Записаны ответы сотрудника на {payload.day}-й день.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/cards/{card_id}/admission")
def set_admission(card_id: int, payload: AdmissionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    if card.track.code not in {"warehouse", "retail"}:
        raise HTTPException(status_code=400, detail="Для опта, RAGEX и офиса самостоятельность закрывается на 30-й день")
    if not can_edit_items(user, card) or not editable(card):
        raise HTTPException(status_code=403, detail="Допуск ставит наставник, руководитель или кадры")
    if not day_reached(card, 14):
        raise HTTPException(status_code=400, detail="Допуск открывается на 14-й день")
    if payload.value == "caveat" and len(payload.note.strip()) < 8:
        raise HTTPException(status_code=400, detail="Оговорку нужно записать: что именно человек ещё не тянет")
    card.admission = payload.value
    card.admission_note = payload.note.strip() if payload.value == "caveat" else ""
    card.admission_date = today() if payload.value != "none" else None
    add_event(db, card, user.full_name, f"Допуск: {payload.value}.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/cards/{card_id}/day30")
def set_day30(card_id: int, payload: Day30In, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    if not can_manage(user, card) or not editable(card):
        raise HTTPException(status_code=403, detail="30-й день закрывает руководитель точки или кадры")
    if card.probation_days < 30 or not day_reached(card, 30):
        raise HTTPException(status_code=400, detail="Точка 30-го дня ещё не наступила")
    reason = payload.reason.strip()
    if payload.choice == "still_with_mentor":
        if len(reason) < 8:
            raise HTTPException(status_code=400, detail="Напишите, почему человек ещё с наставником")
        if payload.recheck_date is None or payload.recheck_date < today() or payload.recheck_date > today() + timedelta(days=14):
            raise HTTPException(status_code=400, detail="Дата повторной проверки — в пределах двух недель")
    if payload.choice == "role_unfit":
        if len(reason) < 8:
            raise HTTPException(status_code=400, detail="Напишите, почему роль не подходит")
        card.separation_started = True
    card.day30_choice = payload.choice
    card.day30_reason = reason
    card.day30_recheck_date = payload.recheck_date if payload.choice == "still_with_mentor" else None
    add_event(db, card, user.full_name, "Закрыта точка 30-го дня.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/cards/{card_id}/day60")
def set_day60(card_id: int, payload: Day60In, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    if not can_edit_items(user, card) or not editable(card):
        raise HTTPException(status_code=403, detail="60-й день отмечает наставник, руководитель или кадры")
    if card.probation_days <= 60 or not day_reached(card, 60):
        raise HTTPException(status_code=400, detail="Точка 60-го дня ещё не наступила")
    note = payload.note.strip()
    if not payload.stable and len(note) < 8:
        raise HTTPException(status_code=400, detail="Напишите, в чём откат")
    card.day60_stable = payload.stable
    card.day60_note = note
    add_event(db, card, user.full_name, "Отмечен 60-й день.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/cards/{card_id}/decision")
def set_decision(card_id: int, payload: DecisionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _one(db, user, card_id)
    if not can_manage(user, card):
        raise HTTPException(status_code=403, detail="Решение по испытанию принимает руководитель точки или кадры")
    if card.stage in ("closed", "dismissed"):
        raise HTTPException(status_code=400, detail="Решение уже закрыто")
    if not decision_unlocked(card):
        raise HTTPException(
            status_code=400,
            detail=f"Решение откроется {card.probation_end_date.strftime('%d.%m.%Y')} или после запуска расставания",
        )
    if payload.decision == "separate":
        if payload.dismissed_date is None:
            raise HTTPException(status_code=400, detail="Для расставания нужна дата увольнения")
        if payload.dismissed_date < card.start_date or payload.dismissed_date > today():
            raise HTTPException(status_code=400, detail="Дата увольнения — не раньше выхода и не в будущем")
        card.dismissed_date = payload.dismissed_date
        card.separation_started = True
    elif payload.decision == "transfer":
        if len(payload.transfer_title.strip()) < 3:
            raise HTTPException(status_code=400, detail="Напишите должность внутри точки")
        card.transfer_title = payload.transfer_title.strip()
    card.probation_decision = payload.decision
    card.probation_decision_comment = payload.comment.strip()
    card.probation_decision_date = today()
    add_event(db, card, user.full_name, "Записано решение по испытанию.")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.post("/signals/{signal_id}/resolve")
def resolve_signal(signal_id: int, payload: ResolveIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Сигнал не найден")
    card = _one(db, user, signal.card_id)
    view = signal_view(signal, user, card, today())
    if not view["can_resolve"]:
        raise HTTPException(status_code=403, detail="Этот сигнал вам не на разбор")
    comment = payload.comment.strip()
    spec = desired_signals(card).get(signal.code, {})
    fingerprint = spec.get("fingerprint", signal.fingerprint)
    if payload.resolution == "fixed":
        if signal.code not in JUDGMENT_CODES:
            raise HTTPException(status_code=400, detail="Этот сигнал закроется сам, когда условие будет закрыто в карточке")
        if len(comment) < 8:
            raise HTTPException(status_code=400, detail="Напишите, что именно поправили")
        signal.status = "resolved"
        signal.resolution = "fixed"
        signal.comment = comment
        signal.fingerprint = fingerprint
        signal.resolved_at = now()
    elif payload.resolution == "recheck":
        if len(comment) < 8:
            raise HTTPException(status_code=400, detail="Напишите, что проверить в следующий раз")
        if payload.recheck_date is None or payload.recheck_date < today() or payload.recheck_date > today() + timedelta(days=14):
            raise HTTPException(status_code=400, detail="Дата повторной проверки — в пределах двух недель")
        signal.status = "waiting_recheck"
        signal.resolution = "recheck"
        signal.comment = comment
        signal.recheck_date = payload.recheck_date
        signal.fingerprint = fingerprint
    elif payload.resolution == "separation":
        if len(comment) < 8:
            raise HTTPException(status_code=400, detail="Напишите, почему запускаете расставание")
        signal.status = "resolved"
        signal.resolution = "separation"
        signal.comment = comment
        signal.fingerprint = fingerprint
        signal.resolved_at = now()
        card.separation_started = True
        if payload.dismissed_date:
            if payload.dismissed_date < card.start_date or payload.dismissed_date > today():
                raise HTTPException(status_code=400, detail="Дата увольнения — не раньше выхода и не в будущем")
            card.dismissed_date = payload.dismissed_date
            card.probation_decision = "separate"
            card.probation_decision_comment = comment
            card.probation_decision_date = today()
    add_event(db, card, user.full_name, f"Разбор сигнала «{signal.title}».")
    sync_card(db, card, actor=user.full_name)
    db.commit()
    return card_detail(_one(db, user, card.id), user)


@router.get("/queue")
def queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cards = _visible(db, user).all()
    _sync_many(db, cards)
    db.commit()
    cards = _visible(db, user).all()
    current = today()
    rows = []
    waiting = []
    for card in cards:
        brief = card_brief(card, current)
        for signal in card.signals:
            if signal.status == "waiting_recheck":
                waiting.append({**brief, "signal": signal_view(signal, user, card, current)})
            elif signal.status == "open":
                if user.role == "hr" and signal.severity != "red":
                    continue
                rows.append({**brief, "signal": signal_view(signal, user, card, current)})
    rows.sort(key=lambda row: (not row["signal"]["overdue"], row["signal"]["severity"] != "red", row["signal"]["opened_at"] or ""))
    return {"items": rows, "waiting": waiting}


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cards = _visible(db, user).all()
    _sync_many(db, cards)
    db.commit()
    cards = _visible(db, user).all()
    departments = db.query(Department).order_by(Department.id).all()
    if user.role != "hr":
        allowed = {department.id for department in user.departments}
        departments = [department for department in departments if department.id in allowed]
        people_query = db.query(BaselinePerson).filter(BaselinePerson.department_id.in_(allowed or [-1]))
    else:
        people_query = db.query(BaselinePerson)
    people = people_query.all()
    return build_summary(cards, people, departments)


@router.get("/templates")
def templates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    del user
    tracks = db.query(Track).options(selectinload(Track.templates)).order_by(Track.id).all()
    payload = []
    for track in tracks:
        items = sorted(track.templates, key=lambda row: row.sort_order)
        critical = sum(1 for item in items if item.is_active and item.is_critical and item.include_mode in ("always", "position"))
        payload.append(
            {
                "code": track.code,
                "name": track.name,
                "critical_count": critical,
                "critical_limit": 5,
                "items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "day": item.checkpoint_day,
                        "is_critical": item.is_critical,
                        "include_mode": item.include_mode,
                        "position_code": item.position_code,
                        "is_active": item.is_active,
                    }
                    for item in items
                ],
            }
        )
    return payload


@router.post("/tracks/{track_code}/items")
def add_template(
    track_code: str,
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_hr),
):
    track = db.query(Track).filter(Track.code == track_code).one_or_none()
    if track is None:
        raise HTTPException(status_code=404, detail="Трек не найден")
    if payload.is_critical and _critical_count(db, track.id) >= 5:
        raise HTTPException(
            status_code=400,
            detail="В треке уже пять критических пунктов. Снимите критичность с другого или добавьте пункт обычным.",
        )
    last = (
        db.query(ChecklistTemplate)
        .filter(ChecklistTemplate.track_id == track.id)
        .order_by(ChecklistTemplate.sort_order.desc())
        .first()
    )
    row = ChecklistTemplate(
        track_id=track.id,
        code=f"custom_{track.code}_{int(now().timestamp())}",
        checkpoint_day=payload.checkpoint_day,
        is_critical=payload.is_critical,
        include_mode="always",
        title=payload.title.strip(),
        sort_order=(last.sort_order + 1) if last else 1,
        is_active=True,
    )
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.patch("/templates/{template_id}")
def patch_template(
    template_id: int,
    payload: TemplatePatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_hr),
):
    del user
    row = db.get(ChecklistTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Пункт не найден")
    if payload.is_critical is True and not row.is_critical and row.include_mode in ("always", "position"):
        if _critical_count(db, row.track_id) >= 5:
            raise HTTPException(status_code=400, detail="Лимит — пять критических пунктов на трек")
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.is_critical is not None:
        row.is_critical = payload.is_critical
    db.commit()
    return {"ok": True}


@router.post("/demo/reset")
def reset_demo(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    del user
    db.expunge_all()
    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(text(f"TRUNCATE TABLE `{table.name}`"))
    db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    db.commit()
    seed_all(db)
    db.commit()
    return {"ok": True}


def _critical_count(db: Session, track_id: int) -> int:
    return (
        db.query(ChecklistTemplate)
        .filter(
            ChecklistTemplate.track_id == track_id,
            ChecklistTemplate.is_active.is_(True),
            ChecklistTemplate.is_critical.is_(True),
            ChecklistTemplate.include_mode.in_(("always", "position")),
        )
        .count()
    )
