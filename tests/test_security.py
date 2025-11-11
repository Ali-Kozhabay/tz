from app.utils.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    password = "Str0ngPass!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_jwt_cycle_contains_subject_and_role():
    token = create_access_token(42, "member")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "member"
    assert payload["type"] == "access"
