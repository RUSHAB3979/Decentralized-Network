"""This machine's node id: stable, public, and not a secret.

Why this is not in agent/core/creds.py
--------------------------------------
`creds.py` is hand-built per ADR 0002 and deliberately unwritten, so it is
worth being precise about why this module is allowed to exist beside it. A
node id is an *identifier*, like a username: it says which machine is
speaking. A credential is a *proof*, and it says the speaker is who it claims
to be. This file only produces the first. Nothing here is secret, nothing here
grants access, and losing the file below costs a provider their tenure record
and nothing else.

The distinction has a consequence that has to stay visible: because the id is
public and unproven, anyone can send a heartbeat claiming to be any node. That
is a known, accepted property of M1 -- see
docs/adr/0004-m1-unauthenticated-heartbeat.md -- and it stops being acceptable
the moment a lease or a payout attaches to a node id. When creds.py is written,
this module stays as it is and gains a sibling that signs its claims.

Why derive rather than generate
-------------------------------
The id is derived from the Windows MachineGuid, which survives app reinstalls
and upgrades. A freshly generated random id would not: a provider who
reinstalls the app would appear as a brand new node, their registration history
would be orphaned, and the fleet would slowly fill with rows for machines that
still exist under a different name. The derived value is still written to disk
and preferred on subsequent reads, so that if the derivation inputs ever change
underneath us -- a Windows repair install rewrites MachineGuid -- the machine
keeps the identity it already registered with.

The GUID is hashed rather than sent. It is a stable hardware-ish identifier
that also appears in unrelated Microsoft telemetry, so forwarding it raw would
make our node ids correlatable with other datasets for no benefit.
"""

from __future__ import annotations

import hashlib
import os
import socket
import uuid
from pathlib import Path

# Namespace prefix in the hash input. Without it, two systems that both hash
# the MachineGuid would derive the same identifier, which quietly turns our
# node id into a cross-system join key.
_SALT = b"p2p-compute-marketplace/node-id/v1"

_FILENAME = "node_id"


def state_dir() -> Path:
    """Where the agent keeps its own files.

    %LOCALAPPDATA% rather than the install directory: Program Files is not
    writable by a standard user, and a provider who runs the app without
    administrator rights is the common case, not the exception.
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "GPUProvider"


def _machine_guid() -> str | None:
    """HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid, or None off Windows."""
    try:
        import winreg  # noqa: PLC0415 - Windows-only, imported where it is used
    except ImportError:
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            # The registry key is 64-bit; a 32-bit Python would otherwise be
            # redirected to Wow6432Node and read a different (or absent) value.
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(value) or None
    except OSError:
        return None


def _derive() -> str:
    """A 32-character hex id from stable machine facts.

    Falls back to a random UUID when MachineGuid is unavailable -- a non-Windows
    developer machine, or a locked-down registry. That fallback is not stable
    across runs by itself, which is exactly why the caller persists the result.
    """
    seed = _machine_guid() or uuid.uuid4().hex
    digest = hashlib.sha256(_SALT + seed.encode("utf-8")).hexdigest()
    # Truncated to 32 hex characters. Collision risk at any plausible fleet
    # size is negligible, and a shorter id is one a human can read back over a
    # support call. It also satisfies the NODE_ID pattern in
    # orchestrator/models.py, which caps ids at 64 characters.
    return digest[:32]


def node_id() -> str:
    """This machine's node id, creating and persisting it on first call.

    Read-then-write rather than write-every-time: the file is the authority
    once it exists, so the id cannot drift if the derivation changes.
    A write failure is not fatal. A provider on a machine where
    %LOCALAPPDATA% is unwritable should still be able to register and earn;
    they simply re-derive the same id next launch, which is the normal case
    anyway since the derivation is deterministic.
    """
    path = state_dir() / _FILENAME
    try:
        existing = path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    except OSError:
        pass

    value = _derive()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    except OSError:
        pass
    return value


def hostname() -> str:
    return socket.gethostname()


# ---------------------------------------------------------------------------
# The node's transport credential.
#
# Kept beside node_id because they are two halves of one identity: node_id says
# which machine this is, the token proves it. They are separate files so that
# losing the token -- which is expected, on every re-registration -- never
# threatens the id, which must survive reinstalls.
#
# HAND-BUILT SEAM, stated plainly: this writes the secret in plaintext to
# %LOCALAPPDATA%. Anyone with local access to the provider's machine can read it
# and impersonate the node. Doing this properly means DPAPI (CryptProtectData,
# user scope), which ties the ciphertext to the Windows account, and that is
# agent/core/creds.py's job -- hand-built under ADR 0002 and still raising
# NotImplementedError. The header of this module already draws the
# identifier-versus-proof line; this is the proof half, parked here in its
# weakest form until the real thing lands.
# ---------------------------------------------------------------------------

_TOKEN_FILENAME = "node_token"


def node_token() -> str | None:
    """The current credential, or None if this node has not registered yet."""
    try:
        value = (state_dir() / _TOKEN_FILENAME).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def store_node_token(token: str) -> bool:
    """Persist a freshly issued credential. Returns whether it was written.

    A write failure is reported rather than raised. The agent can still
    register, heartbeat and show a provider their machine's status without this
    -- it simply cannot claim work, which is a degradation the caller can log
    honestly instead of a crash on startup.
    """
    path = state_dir() / _TOKEN_FILENAME
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token, encoding="utf-8")
        return True
    except OSError:
        return False


def clear_node_token() -> None:
    """Discard a credential the orchestrator has rejected.

    Called when a claim comes back 401. Removing the file makes the next
    registration mint a fresh token, so a node whose credential was rotated
    elsewhere heals itself instead of failing every claim until someone
    restarts the app.
    """
    try:
        (state_dir() / _TOKEN_FILENAME).unlink()
    except OSError:
        pass
