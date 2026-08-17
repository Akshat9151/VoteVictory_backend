import pytest
from app.core.security import (
    compute_ballot_hash,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    generate_ballot_nonce,
    generate_recovery_codes,
    generate_totp_secret,
    get_password_hash,
    hash_token,
    verify_password,
    verify_totp,
)
import pyotp


def test_password_hashing_argon2id():
    raw_pass = "EnterpriseSuperSecret123!"
    hashed = get_password_hash(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_access_token_generation_and_decode():
    sub = "user_uuid_1001"
    org_id = "org_uuid_5001"
    role = "ADMIN"
    permissions = ["election.create", "voter.checkin"]

    token = create_access_token(
        subject=sub,
        organization_id=org_id,
        role=role,
        permissions=permissions
    )
    assert isinstance(token, str)

    claims = decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == sub
    assert claims["org_id"] == org_id
    assert claims["role"] == role
    assert "voter.checkin" in claims["permissions"]


def test_refresh_token_cryptography():
    raw_token, token_hash = create_refresh_token(subject="user_123")
    assert len(raw_token) >= 64
    assert hash_token(raw_token) == token_hash
    assert hash_token("different_token") != token_hash


def test_mfa_totp_verification():
    secret = generate_totp_secret()
    assert len(secret) == 32
    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    assert verify_totp(secret, current_code) is True
    assert verify_totp(secret, "000000") is False


def test_ballot_hmac_serial_hash():
    election_id = "elec_999"
    nonce1 = generate_ballot_nonce()
    nonce2 = generate_ballot_nonce()
    
    hash1 = compute_ballot_hash(election_id, nonce1)
    hash2 = compute_ballot_hash(election_id, nonce2)

    assert len(hash1) == 64
    assert hash1 != hash2
    assert compute_ballot_hash(election_id, nonce1) == hash1
