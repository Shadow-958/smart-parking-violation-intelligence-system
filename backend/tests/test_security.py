"""
Unit tests for app.core.security. Deliberately DB-free so they can run in
any environment with just the backend's requirements installed — no
Postgres/PostGIS needed, unlike route-level tests for complaints etc.
which will require a test database (added when that module lands).
"""

import os
import time

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost/db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from app.core.security import (  # noqa: E402
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hash_and_verify_roundtrip():
    plain = "correct horse battery staple"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True


def test_wrong_password_fails_verification():
    hashed = hash_password("the-real-password")
    assert verify_password("not-the-real-password", hashed) is False


def test_access_token_roundtrip():
    user_id = "5b1b1a3a-3b3a-4a3a-9a3a-1a2b3c4d5e6f"
    token = create_access_token(subject=user_id, role="officer")

    payload = decode_access_token(token)

    assert payload["sub"] == user_id
    assert payload["role"] == "officer"
    assert "exp" in payload


def test_expired_token_is_rejected():
    from datetime import timedelta

    token = create_access_token(subject="some-user-id", role="citizen", expires_delta=timedelta(seconds=-1))

    try:
        decode_access_token(token)
        assert False, "expected ValueError for an expired token"
    except ValueError:
        pass


def test_tampered_token_is_rejected():
    token = create_access_token(subject="some-user-id", role="citizen")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    try:
        decode_access_token(tampered)
        assert False, "expected ValueError for a tampered token"
    except ValueError:
        pass
