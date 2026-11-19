"""Coordinate enrolment and revocation through the provider credential store."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx

from agent.core import creds
from agent.state import Link, ProviderState

_UNENROLLED = "Enter a one-time key from your provider account."
_VAULT_ERROR = "The Windows credential store is unavailable."
_VAULT_ERRORS = (OSError, RuntimeError)
_KEY_FORMAT = re.compile(r"nf_enrol_[A-Za-z0-9_-]{43}")


class Enrolment:
    """Share access to the credential interface between UI and worker threads."""

    def __init__(self, state: ProviderState, base_url: str) -> None:
        self._state = state
        self._base_url = base_url
        self._lock = threading.Lock()
        self._submitting = threading.Lock()
        self._blocked = False
        self._missing_detail = _UNENROLLED

    def _set_link(self, link: Link, detail: str) -> None:
        self._state.set_link(link, self._base_url, detail)

    def _secure_destination(self) -> bool:
        try:
            url = urlsplit(self._base_url)
        except ValueError:
            return False
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            return False
        return url.scheme == "https" or (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
        )

    def token(self) -> str | None:
        with self._lock:
            if not self._secure_destination():
                self._set_link(Link.CREDENTIAL_ERROR, "Configure an HTTPS orchestrator or use localhost.")
                return None
            if self._blocked:
                return None
            try:
                token = creds.load()
            except _VAULT_ERRORS:
                self._set_link(Link.CREDENTIAL_ERROR, _VAULT_ERROR)
                return None
            if not token:
                self._set_link(Link.UNENROLLED, self._missing_detail)
            return token

    def reject(self, rejected: str) -> None:
        """Clear only the credential that produced the 401."""
        with self._lock:
            if self._blocked:
                return
            try:
                if creds.load() != rejected:
                    return
                creds.clear()
            except _VAULT_ERRORS:
                self._blocked = True
                self._set_link(Link.CREDENTIAL_ERROR, _VAULT_ERROR)
                return
            self._missing_detail = "The node credential was rejected. Generate a new enrolment key."
            self._set_link(Link.UNENROLLED, self._missing_detail)

    def submit(
        self,
        key: str,
        exchange: Callable[[str], str],
    ) -> str | None:
        """Exchange a key once. Return a safe error message or None on success."""
        if not isinstance(key, str):
            return "Enter a valid one-time enrolment key."
        key = key.strip()
        if not _KEY_FORMAT.fullmatch(key):
            return "Enter a valid one-time enrolment key."
        if not self._secure_destination():
            return "Configure an HTTPS orchestrator or use localhost."
        if not self._submitting.acquire(blocking=False):
            return "Enrolment is already in progress."
        try:
            with self._lock:
                try:
                    if creds.load() and not self._blocked:
                        return "This machine already has a credential."
                except _VAULT_ERRORS:
                    return _VAULT_ERROR
            try:
                token = exchange(key)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    return "The key was refused. Generate a new key and try again."
                if exc.response.status_code == 409:
                    return "This machine belongs to another provider account."
                if exc.response.status_code == 404:
                    return "This orchestrator does not support machine enrolment."
                return "The orchestrator could not enrol this machine. Try again with a new key."
            except httpx.RequestError:
                return "The orchestrator did not respond. Generate a new key before retrying."
            except (ValueError, OSError):
                return "The enrolment response could not be verified. Generate a new key."
            with self._lock:
                try:
                    creds.store(token)
                except _VAULT_ERRORS:
                    self._blocked = True
                    try:
                        creds.clear()
                    except _VAULT_ERRORS:
                        pass
                    self._set_link(Link.CREDENTIAL_ERROR, _VAULT_ERROR)
                    return "The key was used, but Windows could not save the credential. Fix the store and generate a new key."
                self._blocked = False
                self._missing_detail = _UNENROLLED
                self._set_link(Link.CONNECTING, "Credential saved. Registering this machine.")
            return None
        finally:
            self._submitting.release()
