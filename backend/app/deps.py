from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_db
from app.models import User
from app.security import read_token


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Нужно войти")
    token = authorization.split(" ", 1)[1].strip()
    try:
        user_id = read_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Сессия истекла, войдите снова") from exc
    user = (
        db.query(User)
        .options(selectinload(User.departments), joinedload(User.location))
        .filter(User.id == user_id)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Сессия истекла, войдите снова")
    return user


def require_hr(user: User = Depends(get_current_user)) -> User:
    if user.role != "hr":
        raise HTTPException(status_code=403, detail="Это действие только у кадров")
    return user
