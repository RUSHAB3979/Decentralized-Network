"""Fail-closed security contract for provider workload execution.

This module deliberately does not launch workloads. It is the security-owned
policy boundary that a platform-specific sandbox runner must satisfy before a
job is admitted and before the node can accept another tenant's job.

The contract is dependency-free so it can be exercised in CI and reused by
both Linux and Windows implementations. Cryptographic verification is injected
by the caller; production callers must use a hardware-backed asymmetric key or
an attested workload identity, not a provider-readable shared secret.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import ipaddress
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Iterable


_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


class WorkloadKind(str, Enum):
    """Workloads understood by the isolation policy."""

    SYNTHETIC = "synthetic"
    INFERENCE = "inference"
    RENDER = "render"
    CLOUD_GAMING = "cloud_gaming"


class SecurityTier(str, Enum):
    """Increasingly strong provider execution tiers."""

    OBSERVED = "observed"
    VETTED_INFERENCE = "vetted_inference"
    ISOLATED = "isolated"


_TIER_RANK = {
    SecurityTier.OBSERVED: 0,
    SecurityTier.VETTED_INFERENCE: 1,
    SecurityTier.ISOLATED: 2,
}

_REQUIRED_TIER = {
    WorkloadKind.SYNTHETIC: SecurityTier.OBSERVED,
    WorkloadKind.INFERENCE: SecurityTier.VETTED_INFERENCE,
    WorkloadKind.RENDER: SecurityTier.ISOLATED,
    WorkloadKind.CLOUD_GAMING: SecurityTier.ISOLATED,
}

# A container, WSL distribution, or Windows Sandbox is not accepted as the
# sole boundary for hostile Blender files or interactive third-party software.
_FULL_VM_SANDBOXES = frozenset({"hyperv-vm", "kvm-vfio"})

# How stale an attestation may be before admission fails closed. Defined once
# and referenced by both `authorize` and `SecurityController.begin`: writing the
# literal in two signatures is how one of them gets tightened and the other
# quietly keeps admitting work against a week-old audit.
DEFAULT_MAXIMUM_AUDIT_AGE = timedelta(days=7)


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _validate_digest(value: str, field_name: str) -> None:
    if not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase sha256 digest")


def _validate_opaque_id(value: str, field_name: str) -> None:
    if not _OPAQUE_ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be an opaque 8-128 character identifier")


@dataclass(frozen=True)
class NodeSecurityPosture:
    """Attested properties used for workload admission.

    ``node_alias`` must be a service-generated pseudonym. Hostnames, usernames,
    MAC addresses, MachineGuid values, and raw hardware serials are forbidden.
    """

    node_alias: str
    tier: SecurityTier
    sandbox_kind: str
    sandbox_version: str
    agent_digest: str
    approved_image_digests: frozenset[str]
    disk_encrypted: bool
    dedicated_gpu: bool
    attested: bool
    last_audit_at: datetime
    eligible_workloads: frozenset[WorkloadKind]

    def __post_init__(self) -> None:
        _validate_opaque_id(self.node_alias, "node_alias")
        _validate_digest(self.agent_digest, "agent_digest")
        for digest in self.approved_image_digests:
            _validate_digest(digest, "approved_image_digests entry")
        if not _aware(self.last_audit_at):
            raise ValueError("last_audit_at must be timezone-aware")
        if not self.sandbox_kind or not self.sandbox_version:
            raise ValueError("sandbox kind and version are required")


@dataclass(frozen=True)
class SandboxPolicy:
    """Immutable, security-reviewed limits for one job."""

    job_alias: str
    workload: WorkloadKind
    image_digest: str
    approved_agent_digests: frozenset[str]
    deadline_seconds: int
    cpu_cores: int
    memory_mb: int
    vram_mb: int
    scratch_mb: int
    allowed_egress_hosts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_opaque_id(self.job_alias, "job_alias")
        _validate_digest(self.image_digest, "image_digest")
        if not self.approved_agent_digests:
            raise ValueError("approved_agent_digests cannot be empty")
        for digest in self.approved_agent_digests:
            _validate_digest(digest, "approved_agent_digests entry")
        for name, value in (
            ("deadline_seconds", self.deadline_seconds),
            ("cpu_cores", self.cpu_cores),
            ("memory_mb", self.memory_mb),
            ("scratch_mb", self.scratch_mb),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.vram_mb < 0:
            raise ValueError("vram_mb cannot be negative")
        if len(set(self.allowed_egress_hosts)) != len(self.allowed_egress_hosts):
            raise ValueError("allowed_egress_hosts cannot contain duplicates")
        for host in self.allowed_egress_hosts:
            if host != host.lower() or not _HOST_RE.fullmatch(host):
                raise ValueError(
                    "egress entries must be lowercase hostnames without ports or paths"
                )
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                raise ValueError("egress entries cannot be IP literals")
            if host == "localhost" or host.endswith((".localhost", ".local")):
                raise ValueError("egress entries cannot name local hosts")


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reasons: tuple[str, ...]


def authorize(
    posture: NodeSecurityPosture,
    policy: SandboxPolicy,
    *,
    now: datetime | None = None,
    maximum_audit_age: timedelta = DEFAULT_MAXIMUM_AUDIT_AGE,
) -> AdmissionDecision:
    """Evaluate admission without modifying node state.

    Every unknown or stale property fails closed. The returned reasons are
    stable machine-readable codes suitable for low-cardinality metrics.
    """

    checked_at = now or datetime.now(timezone.utc)
    if not _aware(checked_at):
        raise ValueError("now must be timezone-aware")

    reasons: list[str] = []
    required = _REQUIRED_TIER[policy.workload]
    if _TIER_RANK[posture.tier] < _TIER_RANK[required]:
        reasons.append("tier_insufficient")
    if policy.workload not in posture.eligible_workloads:
        reasons.append("workload_not_eligible")
    if policy.image_digest not in posture.approved_image_digests:
        reasons.append("image_not_approved")
    if posture.agent_digest not in policy.approved_agent_digests:
        reasons.append("agent_not_approved")
    if checked_at - posture.last_audit_at > maximum_audit_age:
        reasons.append("audit_stale")
    if posture.last_audit_at - checked_at > timedelta(minutes=5):
        reasons.append("audit_timestamp_in_future")

    if required is not SecurityTier.OBSERVED:
        if not posture.attested:
            reasons.append("attestation_missing")
        if not posture.disk_encrypted:
            reasons.append("disk_encryption_missing")

    if required is SecurityTier.ISOLATED:
        if posture.sandbox_kind not in _FULL_VM_SANDBOXES:
            reasons.append("full_vm_boundary_missing")
        if not posture.dedicated_gpu:
            reasons.append("dedicated_gpu_missing")

    return AdmissionDecision(allowed=not reasons, reasons=tuple(reasons))


@dataclass(frozen=True)
class CleanupReceipt:
    """Content-free evidence that a sandbox lifecycle completed.

    The receipt intentionally has no free-form message, filesystem path,
    hostname, customer identity, IP address, prompt, model output, or filename.
    """

    receipt_id: str
    job_alias: str
    node_alias: str
    sandbox_id: str
    workload: WorkloadKind
    image_digest: str
    started_at: datetime
    finished_at: datetime
    process_tree_terminated: bool
    ephemeral_key_destroyed: bool
    volume_destroyed: bool
    temp_paths_removed: bool
    gpu_cleanup_verified: bool
    network_policy_removed: bool
    orphan_scan_passed: bool
    canary_markers_recovered: int
    signer_key_id: str

    def __post_init__(self) -> None:
        for field_name in ("receipt_id", "job_alias", "node_alias", "sandbox_id"):
            _validate_opaque_id(getattr(self, field_name), field_name)
        _validate_digest(self.image_digest, "image_digest")
        if not _aware(self.started_at) or not _aware(self.finished_at):
            raise ValueError("receipt timestamps must be timezone-aware")
        if self.canary_markers_recovered < 0:
            raise ValueError("canary_markers_recovered cannot be negative")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", self.signer_key_id):
            raise ValueError("signer_key_id contains unsupported characters")


def canonical_receipt(receipt: CleanupReceipt) -> bytes:
    """Return the exact UTF-8 bytes that must be signed."""

    payload = asdict(receipt)
    payload["workload"] = receipt.workload.value
    payload["started_at"] = receipt.started_at.astimezone(timezone.utc).isoformat()
    payload["finished_at"] = receipt.finished_at.astimezone(timezone.utc).isoformat()
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class CleanupDecision:
    verified: bool
    reasons: tuple[str, ...]


SignatureVerifier = Callable[[bytes, str, str], bool]


def verify_cleanup(
    receipt: CleanupReceipt,
    signature: str,
    verifier: SignatureVerifier,
) -> CleanupDecision:
    """Verify cleanup evidence and its detached signature."""

    reasons: list[str] = []
    if receipt.finished_at < receipt.started_at:
        reasons.append("timestamps_invalid")
    checks = {
        "process_tree_not_terminated": receipt.process_tree_terminated,
        "ephemeral_key_not_destroyed": receipt.ephemeral_key_destroyed,
        "volume_not_destroyed": receipt.volume_destroyed,
        "temp_paths_not_removed": receipt.temp_paths_removed,
        "gpu_cleanup_not_verified": receipt.gpu_cleanup_verified,
        "network_policy_not_removed": receipt.network_policy_removed,
        "orphan_scan_failed": receipt.orphan_scan_passed,
    }
    reasons.extend(code for code, passed in checks.items() if not passed)
    if receipt.canary_markers_recovered != 0:
        reasons.append("canary_recovered")

    try:
        signature_valid = verifier(canonical_receipt(receipt), signature, receipt.signer_key_id)
    except Exception:  # Verifier failures are denial, never availability bypasses.
        signature_valid = False

    # `is True`, not truthiness. SignatureVerifier is annotated `-> bool` and
    # nothing enforces it, while the whole purpose of the injection point is
    # that callers supply their own cryptography -- which is exactly where a
    # library whose verify() returns a *result object* rather than a bool gets
    # wired in. Under `if not signature_valid` that object is truthy, so every
    # signature would validate and this module would report success. An identity
    # check accepts one value and one value only.
    #
    # A non-bool is reported separately from a bad signature because the two
    # need different responses: `signature_invalid` is a receipt to reject and
    # possibly an attack, `verifier_contract_violation` is an integration this
    # deployment has wired up wrongly and every verdict it produced is suspect.
    # Collapsing them would hide the second behind the noise of the first.
    if signature_valid is not True:
        if signature_valid is False:
            reasons.append("signature_invalid")
        else:
            reasons.append("verifier_contract_violation")

    return CleanupDecision(verified=not reasons, reasons=tuple(reasons))


class SecurityController:
    """Small fail-closed state machine for a single provider node.

    A platform runner wraps this state with durable storage. Any restart with an
    orphaned sandbox must call :meth:`reconcile_startup` before claiming work.
    Quarantine clearance is intentionally absent: it requires an operator audit
    and a separate privileged recovery workflow.
    """

    def __init__(self) -> None:
        self._active_context: tuple[str, str, WorkloadKind, str] | None = None
        self._quarantine_reasons: tuple[str, ...] = ()
        # (payload_digest, signature) of the last receipt this controller
        # accepted, so an identical redelivery is recognised instead of being
        # treated as evidence for a job that is no longer running. See
        # :meth:`finish`. The digest covers every receipt field, receipt_id
        # included, because it is taken over the same canonical bytes that were
        # signed.
        self._completed: tuple[str, str] | None = None

    @property
    def active_job(self) -> str | None:
        return self._active_context[0] if self._active_context else None

    @property
    def quarantined(self) -> bool:
        return bool(self._quarantine_reasons)

    @property
    def quarantine_reasons(self) -> tuple[str, ...]:
        return self._quarantine_reasons

    def can_claim(self) -> bool:
        return not self.quarantined and self._active_context is None

    def begin(
        self,
        posture: NodeSecurityPosture,
        policy: SandboxPolicy,
        *,
        now: datetime | None = None,
        maximum_audit_age: timedelta = DEFAULT_MAXIMUM_AUDIT_AGE,
    ) -> AdmissionDecision:
        """Admit one job, or refuse with reasons.

        `maximum_audit_age` is forwarded to :func:`authorize`. It used to be
        absent here, so a deployment that tightened the window got the default
        anyway: `authorize` refused a three-day-old attestation under a one-day
        policy while `begin` admitted the same node. That is a silent policy
        weakening, and this state machine is the entry point callers are told to
        use -- so it was the version almost everyone would have got.
        """
        if self.quarantined:
            return AdmissionDecision(False, ("node_quarantined",))
        if self._active_context is not None:
            return AdmissionDecision(False, ("job_already_active",))
        decision = authorize(
            posture, policy, now=now, maximum_audit_age=maximum_audit_age
        )
        if decision.allowed:
            self._active_context = (
                policy.job_alias,
                posture.node_alias,
                policy.workload,
                policy.image_digest,
            )
        return decision

    def finish(
        self,
        receipt: CleanupReceipt,
        signature: str,
        verifier: SignatureVerifier,
    ) -> CleanupDecision:
        if self._active_context is None:
            # No job is running. Either this is the same receipt arriving twice,
            # or it is evidence for something this controller never admitted.
            if self._is_redelivery(receipt, signature):
                return CleanupDecision(True, ())
            self._active_context = None
            self._quarantine_reasons = ("receipt_job_mismatch",)
            return CleanupDecision(False, self._quarantine_reasons)
        if receipt.job_alias != self._active_context[0]:
            self._active_context = None
            self._quarantine_reasons = ("receipt_job_mismatch",)
            return CleanupDecision(False, self._quarantine_reasons)
        expected = self._active_context
        if (
            receipt.node_alias != expected[1]
            or receipt.workload is not expected[2]
            or receipt.image_digest != expected[3]
        ):
            self._active_context = None
            self._quarantine_reasons = ("receipt_context_mismatch",)
            return CleanupDecision(False, self._quarantine_reasons)

        decision = verify_cleanup(receipt, signature, verifier)
        self._active_context = None
        if not decision.verified:
            self._quarantine_reasons = decision.reasons
        else:
            self._completed = (
                hashlib.sha256(canonical_receipt(receipt)).hexdigest(),
                signature,
            )
        return decision

    def _is_redelivery(self, receipt: CleanupReceipt, signature: str) -> bool:
        """Whether this is byte-for-byte the receipt already accepted.

        The runner completes cleanup, signs the receipt, sends it, and then the
        process dies before it records that the send succeeded. On restart it
        sends again. Without this, that second delivery quarantined a node whose
        sandbox had in fact been torn down correctly -- and quarantine
        deliberately requires an operator audit to clear, so an ordinary crash
        at an ordinary moment took a healthy provider off the marketplace
        permanently. Every other write in this system tolerates a retry: the
        heartbeat is idempotent by construction and registration is an upsert.
        This was the one place a retry was punished.

        Recognition is deliberately narrow, because "accept it again" is a
        dangerous shape. It requires the canonical signed bytes AND the
        signature to match what was accepted, so it cannot be reached by a
        receipt that differs in any field -- a different sandbox_id, a flipped
        cleanup flag, a recovered canary -- nor by replaying a genuine signature
        against altered content. Anything that is not a perfect duplicate takes
        the quarantine path exactly as before.

        It also cannot resurrect a quarantined node: a controller only records a
        completion after a verified finish, and no path clears quarantine.
        """
        if self._completed is None or self.quarantined:
            return False
        expected_digest, expected_signature = self._completed
        digest = hashlib.sha256(canonical_receipt(receipt)).hexdigest()
        # compare_digest on both halves. The signature is not secret, but a
        # comparison that short-circuits on the first differing byte is a habit
        # worth not forming in a file like this one.
        return hmac.compare_digest(digest, expected_digest) and hmac.compare_digest(
            signature, expected_signature
        )

    def reconcile_startup(self, orphan_sandbox_ids: Iterable[str]) -> bool:
        orphans = tuple(orphan_sandbox_ids)
        if self._active_context is not None or orphans:
            self._active_context = None
            self._quarantine_reasons = ("startup_orphan_detected",)
            return False
        return not self.quarantined
