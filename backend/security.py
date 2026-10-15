"""Password hashing and token lifetime helpers (stdlib only).

Password hashes use ``pbkdf2$<iterations>$<salt hex>$<hash hex>`` with
PBKDF2-HMAC-SHA256. Legacy plaintext values must be migrated before serving
login requests; verification never accepts plaintext.
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
    """Return ``ok`` only for a supported PBKDF2 hash, otherwise ``invalid``."""
    if not isinstance(stored, str) or not stored:
        return "invalid"
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$")
        if algorithm != "pbkdf2":
            return "invalid"
        count = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        if count < 1 or count > 2_000_000 or len(salt) < 8 or len(expected_hash) != 32:
            return "invalid"
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, count
        )
        return "ok" if hmac.compare_digest(actual_hash, expected_hash) else "invalid"
    except (ValueError, TypeError):
        return "invalid"


def token_ttl_days() -> int:
    try:
        days = int(os.getenv("AUTH_TOKEN_TTL_DAYS", "30"))
    except ValueError:
        days = 30
    return max(days, 1)
