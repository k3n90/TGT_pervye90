from __future__ import annotations

import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://pervye:pervye@127.0.0.1:3306/pervye90?charset=utf8mb4",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def wait_for_mysql() -> None:
    last_error: Exception | None = None
    for _ in range(40):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 — ждём, пока поднимется контейнер MySQL
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"MySQL не ответил: {last_error}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
