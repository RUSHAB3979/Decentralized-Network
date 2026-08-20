"""Failure injection against the sandbox admission and cleanup contract.

Per ADR 0002 this module is hand-built because its defects degrade silently: a
sandbox that admits work it should have refused still returns the right answer,
and a cleanup that leaves a tenant's data behind still reports success. Nothing
raises. So the useful test is not "does the happy path work" -- the existing
suite covers that -- but "can I get it to say yes when it must say no".
"""

from __future__ import annotations

import hashlib
import hmac
import itertools
import unittest
from dataclasses import fields, replace
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
SECRET = b"test-only-receipt-key"


def posture(**c):
    base = NodeSecurityPosture(
        node_alias="node_01HZZZZZ", tier=SecurityTier.ISOLATED,
        sandbox_kind="hyperv-vm", sandbox_version="1.0.0",
        agent_digest=AGENT_DIGEST, approved_image_digests=frozenset({IMAGE_DIGEST}),
        disk_encrypted=True, dedicated_gpu=True, attested=True,
        last_audit_at=NOW - timedelta(hours=1),
        eligible_workloads=frozenset(WorkloadKind),
    )
    return replace(base, **c)


def policy(**c):
    base = SandboxPolicy(
        job_alias="job_01HZZZZZZ", workload=WorkloadKind.RENDER,
        image_digest=IMAGE_DIGEST, approved_agent_digests=frozenset({AGENT_DIGEST}),
        deadline_seconds=300, cpu_cores=4, memory_mb=4096, vram_mb=4096,
        scratch_mb=8192, allowed_egress_hosts=("objects.example.test",),
    )
    return replace(base, **c)


def receipt(**c):
    base = CleanupReceipt(
        receipt_id="receipt_01HZZZZZ", job_alias="job_01HZZZZZZ",
        node_alias="node_01HZZZZZ", sandbox_id="sandbox_01HZZZZZ",
        workload=WorkloadKind.RENDER, image_digest=IMAGE_DIGEST,
        started_at=NOW, finished_at=NOW + timedelta(minutes=2),
        process_tree_terminated=True, ephemeral_key_destroyed=True,
        volume_destroyed=True, temp_paths_removed=True,
        gpu_cleanup_verified=True, network_policy_removed=True,
        orphan_scan_passed=True, canary_markers_recovered=0,
        signer_key_id="test-key:v1",
    )
    return replace(base, **c)


def sign(r): return hmac.new(SECRET, canonical_receipt(r), hashlib.sha256).hexdigest()
def good_verifier(payload, signature, key_id):
    if key_id != "test-key:v1":
        return False
    return hmac.compare_digest(signature, hmac.new(SECRET, payload, hashlib.sha256).hexdigest())


CLEANUP_FLAGS = (
    "process_tree_terminated", "ephemeral_key_destroyed", "volume_destroyed",
    "temp_paths_removed", "gpu_cleanup_verified", "network_policy_removed",
    "orphan_scan_passed",
)


class TierEscalation(unittest.TestCase):
    """No combination of other properties may substitute for the tier."""

    def test_no_flag_combination_lets_a_weak_tier_run_render(self):
        # Brute force: every posture permutation at a tier below ISOLATED must
        # still refuse RENDER. If any of these passes, a provider could earn the
        # highest-risk workload by flipping booleans it controls.
        weak = [SecurityTier.OBSERVED, SecurityTier.VETTED_INFERENCE]
        combos = itertools.product([True, False], repeat=3)
        admitted = []
        for tier in weak:
            for attested, disk, gpu in combos:
                d = authorize(
                    posture(tier=tier, attested=attested, disk_encrypted=disk,
                            dedicated_gpu=gpu),
                    policy(workload=WorkloadKind.RENDER), now=NOW,
                )
                if d.allowed:
                    admitted.append((tier, attested, disk, gpu))
        self.assertEqual(admitted, [], f"weak tier admitted render: {admitted}")

    def test_container_boundary_cannot_run_hostile_render(self):
        # A container is explicitly not accepted as the sole boundary for a
        # stranger's .blend file. Try every plausible container-ish name.
        for kind in ("docker", "containerd", "wsl2", "windows-sandbox", "podman", "chroot"):
            d = authorize(posture(sandbox_kind=kind), policy(), now=NOW)
            self.assertFalse(d.allowed, f"{kind} admitted for render")
            self.assertIn("full_vm_boundary_missing", d.reasons)

    def test_eligibility_is_required_even_at_the_highest_tier(self):
        d = authorize(
            posture(eligible_workloads=frozenset({WorkloadKind.INFERENCE})),
            policy(workload=WorkloadKind.RENDER), now=NOW,
        )
        self.assertFalse(d.allowed)
        self.assertIn("workload_not_eligible", d.reasons)


class CleanupMustFailClosed(unittest.TestCase):
    def test_every_single_cleanup_flag_alone_denies(self):
        # One flag false at a time. A gap here means a specific class of tenant
        # residue -- an undestroyed volume, a live process tree -- passes
        # verification while everything else looks clean.
        for flag in CLEANUP_FLAGS:
            r = receipt(**{flag: False})
            d = verify_cleanup(r, sign(r), good_verifier)
            self.assertFalse(d.verified, f"{flag}=False was verified")

    def test_all_flags_false_reports_every_reason(self):
        r = receipt(**{f: False for f in CLEANUP_FLAGS})
        d = verify_cleanup(r, sign(r), good_verifier)
        self.assertFalse(d.verified)
        self.assertEqual(len(d.reasons), len(CLEANUP_FLAGS))

    def test_any_recovered_canary_denies(self):
        # A canary that came back means tenant data survived the wipe.
        for n in (1, 2, 1000):
            r = receipt(canary_markers_recovered=n)
            self.assertFalse(verify_cleanup(r, sign(r), good_verifier).verified)

    def test_a_verifier_that_throws_is_denial_not_bypass(self):
        def exploding(payload, signature, key_id):
            raise RuntimeError("HSM unreachable")
        r = receipt()
        d = verify_cleanup(r, sign(r), exploding)
        self.assertFalse(d.verified)
        self.assertIn("signature_invalid", d.reasons)

    def test_signature_is_bound_to_every_receipt_field(self):
        # Re-sign nothing: take a valid signature and mutate each field. If any
        # field is outside the signed bytes, a provider could forge that part of
        # the evidence while keeping a genuine signature.
        base = receipt()
        good = sign(base)
        mutations = {
            "receipt_id": "receipt_OTHERXX", "job_alias": "job_OTHERXXX",
            "node_alias": "node_OTHERXX", "sandbox_id": "sandbox_OTHER",
            "canary_markers_recovered": 0, "process_tree_terminated": True,
        }
        for field, value in mutations.items():
            if getattr(base, field) == value:
                continue
            tampered = replace(base, **{field: value})
            d = verify_cleanup(tampered, good, good_verifier)
            self.assertFalse(d.verified, f"tampering {field} kept a valid signature")


class CanonicalisationStability(unittest.TestCase):
    def test_same_instant_in_a_different_timezone_signs_identically(self):
        # A runner in IST and one in UTC must produce the same bytes for the
        # same moment, or signatures fail for reasons that look like tampering.
        utc = receipt()
        ist = replace(
            utc,
            started_at=utc.started_at.astimezone(timezone(timedelta(hours=5, minutes=30))),
            finished_at=utc.finished_at.astimezone(timezone(timedelta(hours=5, minutes=30))),
        )
        self.assertEqual(canonical_receipt(utc), canonical_receipt(ist))

    def test_canonical_bytes_cover_every_declared_field(self):
        # Guards against a field being added to the dataclass and silently
        # left out of the signed payload.
        blob = canonical_receipt(receipt()).decode()
        for f in fields(CleanupReceipt):
            self.assertIn(f'"{f.name}"', blob, f"{f.name} is not in the signed bytes")


class QuarantineIsTerminal(unittest.TestCase):
    def _quarantine(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        bad = receipt(volume_destroyed=False)
        c.finish(bad, sign(bad), good_verifier)
        return c

    def test_failed_cleanup_quarantines_and_blocks_all_further_work(self):
        c = self._quarantine()
        self.assertTrue(c.quarantined)
        self.assertFalse(c.can_claim())
        d = c.begin(posture(), policy(job_alias="job_NEXTONEX"), now=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("node_quarantined", d.reasons)

    def test_no_public_method_clears_quarantine(self):
        # Clearance is meant to require an operator audit. If any public call
        # resets it, a node can wipe its own record of a failed wipe.
        c = self._quarantine()
        c.reconcile_startup([])
        c.begin(posture(), policy(), now=NOW)
        c.can_claim()
        self.assertTrue(c.quarantined, "quarantine was cleared by ordinary calls")

    def test_startup_with_an_orphan_quarantines(self):
        c = SecurityController()
        self.assertFalse(c.reconcile_startup(["sandbox_LEFTOVER"]))
        self.assertTrue(c.quarantined)


class TenantSeparation(unittest.TestCase):
    def test_a_receipt_for_another_job_quarantines(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        other = receipt(job_alias="job_SOMEONEEL")
        d = c.finish(other, sign(other), good_verifier)
        self.assertFalse(d.verified)
        self.assertTrue(c.quarantined)

    def test_a_receipt_for_another_node_quarantines(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        other = receipt(node_alias="node_SOMEONEE")
        d = c.finish(other, sign(other), good_verifier)
        self.assertFalse(d.verified)
        self.assertIn("receipt_context_mismatch", d.reasons)

    def test_a_receipt_claiming_a_different_image_quarantines(self):
        # Swapping the image after admission is how you run something other
        # than what was approved and still produce clean-looking evidence.
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        other = receipt(image_digest="sha256:" + "c" * 64)
        d = c.finish(other, sign(other), good_verifier)
        self.assertFalse(d.verified)

    def test_second_job_cannot_start_while_one_is_active(self):
        c = SecurityController()
        self.assertTrue(c.begin(posture(), policy(), now=NOW).allowed)
        d = c.begin(posture(), policy(job_alias="job_SECONDXXX"), now=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("job_already_active", d.reasons)


class EgressPolicy(unittest.TestCase):
    def test_ip_literals_and_local_names_are_refused(self):
        for host in ("169.254.169.254", "127.0.0.1", "::1", "localhost",
                     "foo.localhost", "printer.local", "10.0.0.5"):
            with self.assertRaises(ValueError, msg=f"{host} was accepted"):
                policy(allowed_egress_hosts=(host,))

    def test_case_and_shape_are_enforced(self):
        for host in ("Objects.Example.Test", "objects.example.test:443",
                     "http://objects.example.test", "objects.example.test/path",
                     "objects..example.test", "-leading.example.test"):
            with self.assertRaises(ValueError, msg=f"{host} was accepted"):
                policy(allowed_egress_hosts=(host,))

    def test_cloud_metadata_by_name_is_currently_allowed(self):
        """RC-04. Characterisation, not a correctness assertion.

        IP literals are refused, 169.254.169.254 included. A *name* that
        resolves to that same link-local address is accepted by the format
        check. The allowlist is security-reviewed by a human, so this is a
        policy-authoring hazard rather than a contract defect -- recorded so it
        is a known one, and so this test fails loudly if the behaviour is ever
        tightened without updating the register.
        """
        p = policy(allowed_egress_hosts=("metadata.google.internal",))
        self.assertIn("metadata.google.internal", p.allowed_egress_hosts)


class FixedFindings(unittest.TestCase):
    """Regression tests for RC-01..RC-03, fixed 2026-08-20.

    These began as `OpenFindings`, asserting the defective behaviour so that a
    fix would turn them red and force the register to be updated in the same
    change. That worked for RC-01 and RC-02. It did NOT work for RC-03: the
    test asserted that `begin()` uses the seven-day default, which stayed true
    after the fix, because passing no argument still selects the default. The
    finding was that the parameter could not be supplied at all, so the sharp
    characterisation would have been `assertRaises(TypeError)`. Recorded because
    the mechanism is only as good as the property each test picks.
    """

    # -- RC-01 ------------------------------------------------------------

    def test_a_non_bool_verifier_return_is_refused(self):
        r = receipt()
        for ret in ("yes", 1, [1], object(), "", 0, None):
            d = verify_cleanup(r, sign(r), lambda p, s, k, v=ret: v)
            self.assertFalse(d.verified, f"verifier returning {ret!r} was accepted")

    def test_a_broken_verifier_is_reported_apart_from_a_bad_signature(self):
        # Different responses: one is a receipt to reject, the other is an
        # integration that has been wired up wrongly and whose every past
        # verdict is suspect.
        r = receipt()
        broken = verify_cleanup(r, sign(r), lambda p, s, k: "yes")
        self.assertIn("verifier_contract_violation", broken.reasons)
        self.assertNotIn("signature_invalid", broken.reasons)

        bad_sig = verify_cleanup(r, "wrong", good_verifier)
        self.assertIn("signature_invalid", bad_sig.reasons)
        self.assertNotIn("verifier_contract_violation", bad_sig.reasons)

    def test_a_genuine_bool_still_works_both_ways(self):
        r = receipt()
        self.assertTrue(verify_cleanup(r, sign(r), good_verifier).verified)
        self.assertFalse(verify_cleanup(r, "nope", good_verifier).verified)

    # -- RC-02 ------------------------------------------------------------

    def test_an_identical_redelivery_is_accepted_without_quarantine(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        r = receipt()
        first = c.finish(r, sign(r), good_verifier)
        second = c.finish(r, sign(r), good_verifier)
        third = c.finish(r, sign(r), good_verifier)
        self.assertTrue(first.verified)
        self.assertTrue(second.verified, "a retried finish quarantined a healthy node")
        self.assertTrue(third.verified)
        self.assertFalse(c.quarantined)
        self.assertTrue(c.can_claim())

    def test_a_near_miss_redelivery_still_quarantines(self):
        # The dangerous shape. Recognition must be byte-exact, or "accept it
        # again" becomes a way to substitute weaker evidence for the receipt
        # that was actually verified.
        for changed in (
            {"sandbox_id": "sandbox_OTHERX"},
            {"volume_destroyed": False},
            {"canary_markers_recovered": 3},
            {"finished_at": NOW + timedelta(minutes=9)},
            {"signer_key_id": "other-key:v1"},
        ):
            c = SecurityController()
            c.begin(posture(), policy(), now=NOW)
            good = receipt()
            self.assertTrue(c.finish(good, sign(good), good_verifier).verified)

            tampered = replace(good, **changed)
            d = c.finish(tampered, sign(tampered), good_verifier)
            self.assertFalse(d.verified, f"near-miss {changed} was accepted as a retry")
            self.assertTrue(c.quarantined, f"near-miss {changed} did not quarantine")

    def test_a_replayed_signature_over_altered_content_is_refused(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        good = receipt()
        signature = sign(good)
        self.assertTrue(c.finish(good, signature, good_verifier).verified)

        # Same signature, different receipt. Matching one half is not enough.
        tampered = replace(good, sandbox_id="sandbox_OTHERX")
        self.assertFalse(c.finish(tampered, signature, good_verifier).verified)
        self.assertTrue(c.quarantined)

    def test_redelivery_cannot_resurrect_a_quarantined_node(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        good = receipt()
        c.finish(good, sign(good), good_verifier)
        c.begin(posture(), policy(job_alias="job_SECONDXXX"), now=NOW)
        stray = receipt(job_alias="job_SECONDXXX", volume_destroyed=False)
        c.finish(stray, sign(stray), good_verifier)
        self.assertTrue(c.quarantined)

        # The earlier good receipt must not talk the node back to health.
        d = c.finish(good, sign(good), good_verifier)
        self.assertFalse(d.verified)
        self.assertTrue(c.quarantined)

    def test_an_old_receipt_arriving_during_a_new_job_still_quarantines(self):
        c = SecurityController()
        c.begin(posture(), policy(), now=NOW)
        first = receipt()
        c.finish(first, sign(first), good_verifier)
        c.begin(posture(), policy(job_alias="job_SECONDXXX"), now=NOW)
        d = c.finish(first, sign(first), good_verifier)
        self.assertFalse(d.verified, "a stale receipt was accepted mid-job")
        self.assertTrue(c.quarantined)

    def test_a_receipt_for_a_job_never_admitted_still_quarantines(self):
        c = SecurityController()
        r = receipt()
        d = c.finish(r, sign(r), good_verifier)
        self.assertFalse(d.verified)
        self.assertIn("receipt_job_mismatch", d.reasons)

    # -- RC-03 ------------------------------------------------------------

    def test_begin_forwards_a_tighter_audit_window(self):
        stale = posture(last_audit_at=NOW - timedelta(days=3))
        d = SecurityController().begin(
            stale, policy(), now=NOW, maximum_audit_age=timedelta(days=1)
        )
        self.assertFalse(d.allowed, "begin ignored the tighter window")
        self.assertIn("audit_stale", d.reasons)

    def test_begin_and_authorize_agree_on_the_same_window(self):
        stale = posture(last_audit_at=NOW - timedelta(days=3))
        for window, expected in ((timedelta(days=1), False), (timedelta(days=7), True)):
            direct = authorize(stale, policy(), now=NOW, maximum_audit_age=window)
            viac = SecurityController().begin(
                stale, policy(), now=NOW, maximum_audit_age=window
            )
            self.assertEqual(direct.allowed, expected)
            self.assertEqual(
                viac.allowed, direct.allowed,
                f"begin and authorize disagreed at {window}",
            )

    def test_the_default_window_is_defined_once(self):
        # Two literals in two signatures is how one gets tightened and the
        # other keeps admitting week-old attestations.
        import inspect

        from security.runtime_contract import DEFAULT_MAXIMUM_AUDIT_AGE

        for fn in (authorize, SecurityController.begin):
            got = inspect.signature(fn).parameters["maximum_audit_age"].default
            self.assertIs(got, DEFAULT_MAXIMUM_AUDIT_AGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
