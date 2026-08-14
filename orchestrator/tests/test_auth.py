"""Passwords and sessions, tested without a database.

Everything here is pure: hashing, verification, and the session-validity
predicate. That is deliberate and matches liveness.py's reasoning -- CI has no
Postgres, so the parts that decide whether someone is who they claim to be must
be testable without one, or they end up untested.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orchestrator import auth

NOW = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_same_password_hashes_differently_every_time():
    # Distinct salts. Without them, two accounts sharing a password would share
    # a digest, and a leaked table would reveal that fact to anyone who looked
    # -- one cracked password would unlock every account that reused it.
    first = auth.hash_password("correct horse battery")
    second = auth.hash_password("correct horse battery")
    assert first != second
    assert auth.verify_password("correct horse battery", first)
    assert auth.verify_password("correct horse battery", second)


def test_wrong_password_is_rejected():
    stored = auth.hash_password("correct horse battery")
    assert not auth.verify_password("Correct horse battery", stored)
    assert not auth.verify_password("", stored)


def test_stored_hash_never_contains_the_password():
    stored = auth.hash_password("hunter2-hunter2")
    assert "hunter2" not in stored


def test_hash_is_self_describing():
    # The cost parameters travel with the digest so they can be raised later
    # without invalidating existing rows. A bare hex digest would force a
    # password reset on every user the day the cost changes.
    stored = auth.hash_password("a-long-enough-password")
    scheme, n, r, p, salt, digest = stored.split("$")
    assert scheme == "scrypt"
    assert int(n) == auth.SCRYPT_N
    assert int(r) == auth.SCRYPT_R
    assert int(p) == auth.SCRYPT_P
    assert bytes.fromhex(salt) and bytes.fromhex(digest)


def test_a_hash_made_with_weaker_parameters_still_verifies():
    # Simulates a row written before the cost was raised. verify_password must
    # read n/r/p from the stored string, not from the current constants.
    import hashlib

    salt = b"0123456789abcdef"
    weak_n = 2**10
    digest = hashlib.scrypt(
        b"legacy-password-x", salt=salt, n=weak_n, r=8, p=1, dklen=32
    )
    stored = f"scrypt${weak_n}$8$1${salt.hex()}${digest.hex()}"
    assert auth.verify_password("legacy-password-x", stored)
    assert not auth.verify_password("wrong", stored)


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "not-a-hash",
        "scrypt$16384$8",
        "bcrypt$16384$8$1$aa$bb",
        "scrypt$x$8$1$aa$bb",
    ],
)
def test_unreadable_stored_hashes_raise_rather_than_failing_login(stored):
    # A corrupt row is our problem, not the user's. Returning False here would
    # tell someone their correct password is wrong and send them to reset it,
    # while the real fault is in storage.
    with pytest.raises(auth.PasswordFormatError):
        auth.verify_password("anything", stored)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  Rushab@Example.COM ", "rushab@example.com"),
        ("a@b.co", "a@b.co"),
        ("MIXED@Case.Io", "mixed@case.io"),
    ],
)
def test_email_normalisation_prevents_duplicate_accounts(raw, expected):
    assert auth.normalise_email(raw) == expected


def test_session_and_node_tokens_are_stored_only_as_digests():
    secret, digest = auth.issue_session_token()
    assert secret.startswith(auth.SESSION_TOKEN_MARKER)
    assert digest == auth.hash_token(secret)
    assert secret not in digest

    node_secret, node_digest = auth.issue_node_token()
    assert node_secret.startswith(auth.NODE_TOKEN_MARKER)
    assert node_digest == auth.hash_token(node_secret)


def test_tokens_are_unique():
    assert auth.issue_session_token()[0] != auth.issue_session_token()[0]
    assert auth.issue_node_token()[0] != auth.issue_node_token()[0]


def test_session_validity_is_derived_from_the_row():
    future = NOW + timedelta(days=1)
    past = NOW - timedelta(seconds=1)

    assert auth.session_is_valid(future, None, NOW)
    # Expiry needs no sweeper: the same row stops being valid as `now` advances.
    assert not auth.session_is_valid(past, None, NOW)
    # Revocation beats a valid expiry, which is what makes logout work.
    assert not auth.session_is_valid(future, NOW, NOW)
    assert not auth.session_is_valid(None, None, NOW)


def test_session_expiry_is_in_the_future():
    assert auth.session_expiry(NOW) > NOW
