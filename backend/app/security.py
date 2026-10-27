import base64
import hashlib
import hmac
import json
import secrets
import time
from app.config import settings


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${_b64url(salt)}${_b64url(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt64, digest64 = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt, expected = _unb64url(salt64), _unb64url(digest64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url(json.dumps({"sub": str(user_id), "iat": now, "exp": now + settings.jwt_expire_minutes * 60}, separators=(",", ":")).encode())
    unsigned = f"{header}.{body}"
    signature = _b64url(hmac.new(settings.jwt_secret.encode(), unsigned.encode(), hashlib.sha256).digest())
    return f"{unsigned}.{signature}"


def read_token(token: str) -> int | None:
    try:
        header64, body64, signature64 = token.split(".", 2)
        header = json.loads(_unb64url(header64))
        if header.get("alg") != "HS256":
            return None
        unsigned = f"{header64}.{body64}"
        expected = _b64url(hmac.new(settings.jwt_secret.encode(), unsigned.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature64):
            return None
        data = json.loads(_unb64url(body64))
        if int(data.get("exp", 0)) <= int(time.time()):
            return None
        return int(data["sub"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
