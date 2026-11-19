"""Passwords and login sessions.

Split out of main.py rather than added to inference.py, because the two answer
different questions. `inference.py` authenticates a *machine-to-machine* API
key: one secret, presented on every call, compared in constant time.  This file
authenticates a *human*: a password that a person chose, typed, and probably
reused somewhere else.

That difference is the whole reason the hashing is different too.

Why scrypt and not SHA-256
--------------------------
An API key is 32 bytes from `secrets.token_urlsafe`. There is nothing to guess,
so a single SHA-256 is the right cost: fast to verify, impossible to brute
force.

A password is not that. It is short, human-chosen, and frequently reused. If
this database leaks, an attacker with the digests runs a wordlist against them
offline, and with SHA-256 they run billions of guesses per second on a GPU --
the same hardware this marketplace exists to rent out. A password KDF exists to
make that arithmetic bad for them, by being deliberately slow and
memory-hungry.

`hashlib.scrypt` is in the standard library, so this costs no new dependency on
a component that already pins its requirements carefully. argon2 is the more
modern answer and would need `argon2-cffi`; scrypt is a legitimate choice and
the stored format below can carry an argon2 variant later without a migration.

Why the stored digest is self-describing
----------------------------------------
The format is `scrypt$n$r$p$salt$digest`, not a bare hex string. Cost
parameters belong *with* the digest, because raising them later must not
invalidate every existing password. A row hashed at n=2**14 keeps verifying
against its own parameters while new rows use whatever the constant says today.
A bare digest gives you no way to do that except forcing a password reset on
everybody.

Why sessions are opaque tokens, not JWTs
----------------------------------------
A JWT is verified by signature alone, which is exactly what makes logout hard:
the token stays valid until it expires no matter what the server thinks. Fixing
that means keeping a revocation list, which is a database lookup -- the same
lookup a session table already is, with cryptography added on top rather than
instead.

So: a random token, stored hashed, checked against a row. Logout is an UPDATE.
Expiry is read from a column at verification time and never swept by a
background job, for the reason liveness.py sets out at length -- a sweeper that
dies leaves every expired session working forever, and nothing raises.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

# Deliberately above the interactive-login default you will see quoted for
# scrypt. Login is not a hot path -- a human does it once a day -- so hundreds
# of milliseconds is affordable here and expensive for an offline attacker.
#
# maxmem must be raised alongside n: scrypt needs roughly 128 * n * r bytes, and
# hashlib's default ceiling of 32 MiB rejects these parameters with a bare
# ValueError that reads like a bug rather than a configuration limit.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024
SCRYPT_DKLEN = 32

SALT_BYTES = 16

# How long a login lasts. Short enough that a stolen token has a bounded life,
# long enough that a person is not retyping a password mid-session.
SESSION_TTL = timedelta(days=7)

SESSION_TOKEN_MARKER = "nf_sess_"

# Presented to the caller once and never stored in this form.
NODE_TOKEN_MARKER = "nf_node_"


class PasswordFormatError(ValueError):
    """A stored password hash could not be parsed.

    Distinct from "the password is wrong". A malformed row means data
    corruption or a format change that was rolled out badly, and it must not be
    reported to the caller as a failed login -- that would send someone to reset
    a password when the actual problem is in storage.
    """


def hash_password(password: str) -> str:
    """Derive a self-describing scrypt digest for a new or changed password."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM,
        dklen=SCRYPT_DKLEN,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored digest, using that digest's parameters.

    Reads n, r and p out of the stored string rather than the constants above,
    so raising the cost for new passwords does not lock out existing accounts.
    """
    try:
        scheme, n_raw, r_raw, p_raw, salt_hex, digest_hex = stored.split("$")
    except ValueError as exc:
        raise PasswordFormatError(f"unrecognised password hash format: {stored[:16]!r}") from exc

    if scheme != "scrypt":
        raise PasswordFormatError(f"unsupported password hash scheme {scheme!r}")

    try:
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError as exc:
        raise PasswordFormatError("password hash fields are not parseable") from exc

    candidate = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        # Sized from the stored parameters, not the current constants, so an
        # old row hashed at a smaller n still verifies after the cost is raised.
        maxmem=max(SCRYPT_MAXMEM, 256 * n * r),
        dklen=len(expected),
    )
    # compare_digest, not ==. String equality short-circuits on the first
    # differing byte, and the time it takes leaks how much of the digest was
    # guessed correctly.
    return hmac.compare_digest(candidate, expected)


def normalise_email(email: str) -> str:
    """Lowercase and trim, so one human cannot become two accounts.

    Applied before both the uniqueness check and the lookup. Doing it in only
    one of those places is worse than doing it in neither: signup would reject
    `A@x.com` as taken while login for it would find nothing.
    """
    return email.strip().lower()


def issue_session_token() -> tuple[str, str]:
    """Return `(secret, digest)` for a new login session.

    The secret goes to the browser and is never stored. The digest is what the
    table keeps, so a leaked backup is not a set of working logins.
    """
    secret = f"{SESSION_TOKEN_MARKER}{secrets.token_urlsafe(32)}"
    return secret, hash_token(secret)


def issue_enrolment_key() -> tuple[str, str]:
    """Return a single-use provider enrolment key and its storage digest."""
    secret = f"nf_enrol_{secrets.token_urlsafe(32)}"
    return secret, hash_token(secret)


def issue_node_token() -> tuple[str, str]:
    """Return `(secret, digest)` for a provider node's transport credential.

    HAND-BUILT SEAM. This proves a claim-work request came from the machine that
    registered, and nothing more. Storage on the agent side, rotation, and
    binding the credential to the hardware are agent/core/creds.py's job -- that
    module is hand-built under ADR 0002 and still raises NotImplementedError.
    Until it lands, the agent keeps this secret in a plaintext file, and that is
    a known gap rather than an oversight.
    """
    secret = f"{NODE_TOKEN_MARKER}{secrets.token_urlsafe(32)}"
    return secret, hash_token(secret)


def hash_token(secret: str) -> str:
    """SHA-256 of a machine-generated secret.

    Correct here and wrong for passwords: this input is 32 random bytes, so
    there is no wordlist to run against it and no reason to pay a KDF's cost on
    every request.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def session_expiry(now: datetime) -> datetime:
    return now + session_ttl()


def session_ttl() -> timedelta:
    """Read per call so it can be changed without a code change, and varied in tests."""
    try:
        days = int(os.getenv("SESSION_TTL_DAYS", "7"))
    except ValueError:
        return SESSION_TTL
    return timedelta(days=max(1, days))


def session_is_valid(
    expires_at: datetime | None,
    revoked_at: datetime | None,
    now: datetime,
) -> bool:
    """Whether a session row still authenticates its holder.

    Derived at read time from the row's own columns. Nothing marks sessions dead
    on a timer, so there is no sweeper whose death would leave every expired
    session working -- the answer changes on its own as `now` advances.
    """
    if revoked_at is not None:
        return False
    if expires_at is None:
        return False
    return now < expires_at
