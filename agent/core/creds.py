"""Machine identity and the orchestrator credential. HAND-BUILT - see README.md.

Failure mode: a credential stored badly works exactly as well as one stored
well. There is no test that goes red, no traceback, and no moment where the
provider finds out. That is why this is not generated.

Design notes worth settling before writing a line:

- The credential belongs to the *machine*, not the person. A provider with two
  PCs has two of these, and revoking one must not log out the other.
- On Windows the storage answer is almost certainly DPAPI
  (`CryptProtectData`, user scope), not a file in %APPDATA% and not the
  registry. DPAPI ties the ciphertext to the Windows account, so copying the
  file to another machine yields nothing.
- Rotation has to work while the node is running, because the alternative is
  telling providers to reinstall.
- A customer's token must never appear here or anywhere else on this machine.
  It terminates at the gateway. This module handles the provider's own
  credential only.
"""

from __future__ import annotations


def load() -> str | None:
    """Return this machine's orchestrator credential, or None if unenrolled."""
    raise NotImplementedError


def store(credential: str) -> None:
    """Persist the credential so it survives reboot but not exfiltration."""
    raise NotImplementedError


def clear() -> None:
    """Remove the credential. Must leave the machine safely unenrolled."""
    raise NotImplementedError
