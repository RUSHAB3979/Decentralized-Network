from __future__ import annotations

import hashlib
import hmac
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from security.runtime_contract import (
    CleanupReceipt,
    NodeSecurityPosture,
    SandboxPolicy,
    SecurityController,
    SecurityTier,
    WorkloadKind,
    authorize,
    canonical_receipt,
    verify_cleanup,
)


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
AGENT_DIGEST = "sha256:" + "a" * 64
IMAGE_DIGEST = "sha256:" + "b" * 64
TEST_SECRET = b"test-only-receipt-key"


def posture(
    *,
    tier: SecurityTier = SecurityTier.ISOLATED,
    sandbox_kind: str = "hyperv-vm",
    dedicated_gpu: bool = True,
) -> NodeSecurityPosture:
    return NodeSecurityPosture(
        node_alias="node_01HZZZZZ",
        tier=tier,
        sandbox_kind=sandbox_kind,
        sandbox_version="1.0.0",
        agent_digest=AGENT_DIGEST,
        approved_image_digests=frozenset({IMAGE_DIGEST}),
        disk_encrypted=True,
        dedicated_gpu=dedicated_gpu,
        attested=True,
        last_audit_at=NOW - timedelta(hours=1),
        eligible_workloads=frozenset(WorkloadKind),
    )


def policy(workload: WorkloadKind = WorkloadKind.RENDER) -> SandboxPolicy:
    return SandboxPolicy(
        job_alias="job_01HZZZZZZ",
        workload=workload,
        image_digest=IMAGE_DIGEST,
        approved_agent_digests=frozenset({AGENT_DIGEST}),
        deadline_seconds=300,
        cpu_cores=4,
        memory_mb=4096,
        vram_mb=4096,
        scratch_mb=8192,
        allowed_egress_hosts=("objects.example.test",),
    )


def receipt(**changes: object) -> CleanupReceipt:
    base = CleanupReceipt(
        receipt_id="receipt_01HZZZZZ",
        job_alias="job_01HZZZZZZ",
        node_alias="node_01HZZZZZ",
        sandbox_id="sandbox_01HZZZZZ",
        workload=WorkloadKind.RENDER,
        image_digest=IMAGE_DIGEST,
        started_at=NOW,
        finished_at=NOW + timedelta(minutes=2),
        process_tree_terminated=True,
        ephemeral_key_destroyed=True,
        volume_destroyed=True,
        temp_paths_removed=True,
        gpu_cleanup_verified=True,
        network_policy_removed=True,
        orphan_scan_passed=True,
        canary_markers_recovered=0,
        signer_key_id="test-key:v1",
    )
    return replace(base, **changes)


def sign(value: CleanupReceipt) -> str:
    return hmac.new(TEST_SECRET, canonical_receipt(value), hashlib.sha256).hexdigest()


def verifier(payload: bytes, signature: str, key_id: str) -> bool:
    if key_id != "test-key:v1":
        return False
    expected = hmac.new(TEST_SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


class AdmissionTests(unittest.TestCase):
    def test_isolated_render_is_admitted(self) -> None:
        self.assertTrue(authorize(posture(), policy(), now=NOW).allowed)

    def test_observed_node_cannot_run_customer_inference(self) -> None:
        decision = authorize(
            posture(tier=SecurityTier.OBSERVED),
            policy(WorkloadKind.INFERENCE),
            now=NOW,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("tier_insufficient", decision.reasons)

    def test_vetted_inference_is_admitted(self) -> None:
        decision = authorize(
            posture(tier=SecurityTier.VETTED_INFERENCE, sandbox_kind="restricted-process"),
            policy(WorkloadKind.INFERENCE),
            now=NOW,
        )
        self.assertTrue(decision.allowed)

    def test_vetted_node_cannot_run_untrusted_blend(self) -> None:
        decision = authorize(
            posture(tier=SecurityTier.VETTED_INFERENCE), policy(), now=NOW
        )
        self.assertIn("tier_insufficient", decision.reasons)

    def test_container_is_not_a_render_security_boundary(self) -> None:
        decision = authorize(posture(sandbox_kind="docker"), policy(), now=NOW)
        self.assertIn("full_vm_boundary_missing", decision.reasons)

    def test_render_requires_dedicated_gpu(self) -> None:
        decision = authorize(posture(dedicated_gpu=False), policy(), now=NOW)
        self.assertIn("dedicated_gpu_missing", decision.reasons)

    def test_stale_audit_fails_closed(self) -> None:
        stale = replace(posture(), last_audit_at=NOW - timedelta(days=8))
        self.assertIn("audit_stale", authorize(stale, policy(), now=NOW).reasons)

    def test_unapproved_image_fails_closed(self) -> None:
        unapproved = replace(posture(), approved_image_digests=frozenset())
        self.assertIn("image_not_approved", authorize(unapproved, policy(), now=NOW).reasons)

    def test_unapproved_agent_fails_closed(self) -> None:
        changed = replace(posture(), agent_digest="sha256:" + "c" * 64)
        self.assertIn("agent_not_approved", authorize(changed, policy(), now=NOW).reasons)

    def test_policy_rejects_url_in_egress_allowlist(self) -> None:
        with self.assertRaises(ValueError):
            replace(policy(), allowed_egress_hosts=("https://objects.example.test/path",))

    def test_policy_rejects_ip_and_local_egress(self) -> None:
        for host in ("127.0.0.1", "169.254.169.254", "localhost", "printer.local"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                replace(policy(), allowed_egress_hosts=(host,))


class CleanupTests(unittest.TestCase):
    def test_complete_signed_receipt_is_verified(self) -> None:
        value = receipt()
        self.assertTrue(verify_cleanup(value, sign(value), verifier).verified)

    def test_every_required_cleanup_check_fails_closed(self) -> None:
        fields = (
            "process_tree_terminated",
            "ephemeral_key_destroyed",
            "volume_destroyed",
            "temp_paths_removed",
            "gpu_cleanup_verified",
            "network_policy_removed",
            "orphan_scan_passed",
        )
        for field in fields:
            with self.subTest(field=field):
                value = receipt(**{field: False})
                self.assertFalse(verify_cleanup(value, sign(value), verifier).verified)

    def test_recovered_canary_fails_cleanup(self) -> None:
        value = receipt(canary_markers_recovered=1)
        decision = verify_cleanup(value, sign(value), verifier)
        self.assertIn("canary_recovered", decision.reasons)

    def test_bad_signature_fails_cleanup(self) -> None:
        self.assertIn(
            "signature_invalid",
            verify_cleanup(receipt(), "tampered", verifier).reasons,
        )

    def test_receipt_has_no_customer_content_fields(self) -> None:
        encoded = canonical_receipt(receipt()).decode("utf-8")
        for forbidden in ("prompt", "response", "filename", "filepath", "ip_address", "hostname"):
            self.assertNotIn(forbidden, encoded)


class ControllerTests(unittest.TestCase):
    def test_verified_cleanup_allows_the_next_job(self) -> None:
        controller = SecurityController()
        self.assertTrue(controller.begin(posture(), policy(), now=NOW).allowed)
        value = receipt()
        self.assertTrue(controller.finish(value, sign(value), verifier).verified)
        self.assertTrue(controller.can_claim())

    def test_second_job_is_blocked_until_cleanup(self) -> None:
        controller = SecurityController()
        self.assertTrue(controller.begin(posture(), policy(), now=NOW).allowed)
        decision = controller.begin(posture(), policy(), now=NOW)
        self.assertEqual(decision.reasons, ("job_already_active",))

    def test_failed_cleanup_quarantines_node(self) -> None:
        controller = SecurityController()
        controller.begin(posture(), policy(), now=NOW)
        value = receipt(volume_destroyed=False)
        self.assertFalse(controller.finish(value, sign(value), verifier).verified)
        self.assertTrue(controller.quarantined)
        self.assertEqual(
            controller.begin(posture(), policy(), now=NOW).reasons,
            ("node_quarantined",),
        )

    def test_mismatched_receipt_quarantines_node(self) -> None:
        controller = SecurityController()
        controller.begin(posture(), policy(), now=NOW)
        value = receipt(job_alias="job_02HYYYYYY")
        decision = controller.finish(value, sign(value), verifier)
        self.assertEqual(decision.reasons, ("receipt_job_mismatch",))

    def test_wrong_execution_context_receipt_quarantines_node(self) -> None:
        for changes in (
            {"node_alias": "node_02HYYYYYY"},
            {"workload": WorkloadKind.INFERENCE},
            {"image_digest": "sha256:" + "c" * 64},
        ):
            with self.subTest(changes=changes):
                controller = SecurityController()
                controller.begin(posture(), policy(), now=NOW)
                value = receipt(**changes)
                decision = controller.finish(value, sign(value), verifier)
                self.assertEqual(decision.reasons, ("receipt_context_mismatch",))

    def test_startup_orphan_quarantines_node(self) -> None:
        controller = SecurityController()
        self.assertFalse(controller.reconcile_startup(["sandbox_orphan1"]))
        self.assertTrue(controller.quarantined)


if __name__ == "__main__":
    unittest.main()
