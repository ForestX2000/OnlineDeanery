"""Пароли и токены без внешних зависимостей (только stdlib).

Формат хэша: ``pbkdf2$<итераций>$<salt hex>$<hash hex>`` (HMAC-SHA256).
Старые plaintext-записи из ранних сидов принимаются один раз при логине
и тут же мигрируют на хэш (verify_password -> "legacy").
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

ITERATIONS = 200_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> str:
    """Возвращает 'ok' | 'legacy' | 'invalid'.

    'legacy' — совпал старый plaintext-хэш: вызывающий должен перезаписать
    поле свежим hash_password и закоммитить.
    """
    if not isinstance(stored, str) or not stored:
        return "invalid"
    if stored.startswith("pbkdf2$"):
        try:
            _, iters, salt_hex, hash_hex = stored.split("$")
            expected = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"),
                bytes.fromhex(salt_hex), int(iters),
            )
            return "ok" if hmac.compare_digest(expected.hex(), hash_hex) else "invalid"
        except (ValueError, TypeError):
            return "invalid"
    return "legacy" if hmac.compare_digest(password, stored) else "invalid"


def token_ttl_days() -> int:
    try:
        days = int(os.getenv("AUTH_TOKEN_TTL_DAYS", "30"))
    except ValueError:
        days = 30
    return max(days, 1)
