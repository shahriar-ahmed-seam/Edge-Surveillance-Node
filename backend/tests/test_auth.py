import dataclasses

import pytest

from app.api.auth import (
    AuthError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_token_roundtrip(settings):
    token = create_access_token(settings, subject="a@b.com", role="admin")
    payload = decode_token(settings, token)
    assert payload["sub"] == "a@b.com"
    assert payload["role"] == "admin"


def test_token_creation_rejects_over_cap(settings):
    bad = dataclasses.replace(settings, jwt_lifetime_hours=48)
    with pytest.raises(AuthError):
        create_access_token(bad, subject="a@b.com", role="admin")


def test_decode_invalid_token_raises(settings):
    with pytest.raises(AuthError):
        decode_token(settings, "not.a.token")
