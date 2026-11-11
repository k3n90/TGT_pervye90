import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "demo-pervye-90")
PASSWORD = "demo"


def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"pervye90-demo", 120_000).hex()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def make_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=14),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def read_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    return int(payload["sub"])
