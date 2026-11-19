"""Exercise separate account realms against the Postgres used by schema CI."""

from __future__ import annotations

import os
from time import monotonic, sleep
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo

from orchestrator import auth, db, main
from orchestrator.seed_users import seed

PROVIDER_AUTH = "/v1/provider/auth"
ACCOUNT = {"email": "  Pilot@Example.test  ", "password": "pilot-fixture-password"}
KEYS = "/v1/provider/enrolment-keys"
NODES = "/v1/provider/nodes"
JOBS = "/v1/provider/jobs"
NODE = {"node_id": "pilot-node-001", "capability": {"hostname": "PILOT"}}
OTHER_NODE = {**NODE, "node_id": "pilot-node-002"}
HEARTBEAT = {
    "node_id": NODE["node_id"],
    "status": "idle",
    "accepts_work": True,
    "metrics": {"ollama_reachable": True, "local_models": ["fixture:model"]},
}
APPROVAL = f"/v1/operator/providers/nodes/{NODE['node_id']}/inference-approval"


@pytest.fixture
def client(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("set TEST_POSTGRES_DSN to run against a disposable Postgres instance")
    name = f"provider_test_{uuid4().hex}"
    identifier = sql.Identifier(name)
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(identifier))
        try:
            monkeypatch.setenv("DATABASE_URL", make_conninfo(dsn, options=f"-csearch_path={name}"))
            monkeypatch.setenv("SIGNUPS_OPEN", "true")
            monkeypatch.setattr(main, "_schema_error", None)
            with TestClient(main.app) as session:
                assert session.get("/health").status_code == 200
                yield session
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(identifier))


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_provider_sessions_and_customer_sessions_are_separate(client):
    response = client.post(f"{PROVIDER_AUTH}/signup", json=ACCOUNT)
    assert response.status_code == 201
    session = response.json()
    provider = session["provider"]
    assert provider["email"] == "pilot@example.test"
    assert "password_hash" not in provider
    assert client.post(f"{PROVIDER_AUTH}/signup", json=ACCOUNT).status_code == 409
    provider_headers = bearer(session["token"])

    customer = client.post("/v1/auth/signup", json=ACCOUNT)
    assert customer.status_code == 201
    customer_headers = bearer(customer.json()["token"])
    assert client.get(f"{PROVIDER_AUTH}/me", headers=provider_headers).json() == provider
    assert client.get(f"{PROVIDER_AUTH}/me", headers=customer_headers).status_code == 401
    assert client.post(f"{PROVIDER_AUTH}/logout", headers=customer_headers).status_code == 401
    assert client.get("/v1/auth/me", headers=provider_headers).status_code == 401
    assert client.get("/v1/auth/me", headers=customer_headers).status_code == 200

    with db.connect() as conn:
        row = conn.execute("SELECT token_hash FROM provider_sessions").fetchone()
        assert row["token_hash"] == auth.hash_token(session["token"])


def test_provider_login_revocation_and_expiry(client):
    signup = client.post(f"{PROVIDER_AUTH}/signup", json=ACCOUNT)
    assert signup.status_code == 201
    invalid = client.post(f"{PROVIDER_AUTH}/login", json={**ACCOUNT, "password": "wrong"})
    unknown = client.post(f"{PROVIDER_AUTH}/login", json={**ACCOUNT, "email": "other@example.test"})
    assert invalid.status_code == unknown.status_code == 401
    assert invalid.json() == unknown.json()

    login = client.post(f"{PROVIDER_AUTH}/login", json=ACCOUNT)
    assert login.status_code == 200
    headers = bearer(login.json()["token"])
    assert client.get(f"{PROVIDER_AUTH}/me", headers=headers).status_code == 200
    assert client.post(f"{PROVIDER_AUTH}/logout", headers=headers).status_code == 204
    assert client.post(f"{PROVIDER_AUTH}/logout", headers=headers).status_code == 204
    assert client.get(f"{PROVIDER_AUTH}/me", headers=headers).status_code == 401

    original_headers = bearer(signup.json()["token"])
    assert client.get(f"{PROVIDER_AUTH}/me", headers=original_headers).status_code == 200
    with db.connect() as conn:
        conn.execute(
            "UPDATE provider_sessions SET expires_at = now() - interval '1 second' WHERE token_hash = %s",
            (auth.hash_token(signup.json()["token"]),),
        )
    assert client.get(f"{PROVIDER_AUTH}/me", headers=original_headers).status_code == 401


def test_closed_provider_signup_can_be_seeded(client, monkeypatch):
    monkeypatch.setenv("SIGNUPS_OPEN", "false")
    assert client.post(f"{PROVIDER_AUTH}/signup", json=ACCOUNT).status_code == 403
    email, password = seed(ACCOUNT["email"], provider=True, reset=False)
    assert seed(email, provider=True, reset=False) is None
    payload = {"email": email, "password": password}
    assert client.post(f"{PROVIDER_AUTH}/login", json=payload).status_code == 200
    assert client.post("/v1/auth/login", json=payload).status_code == 401


def test_signup_rolls_back_if_session_cannot_be_written(client, monkeypatch):
    def fail_session(_cur, _account):
        raise psycopg.OperationalError("synthetic session insert failure")

    with monkeypatch.context() as failure:
        failure.setattr(main, "_start_provider_session", fail_session)
        assert client.post(f"{PROVIDER_AUTH}/signup", json=ACCOUNT).status_code == 503
    assert client.post(f"{PROVIDER_AUTH}/signup", json=ACCOUNT).status_code == 201


def provider_headers(client, email="pilot@example.test"):
    signup = client.post(f"{PROVIDER_AUTH}/signup", json={**ACCOUNT, "email": email})
    assert signup.status_code == 201
    return bearer(signup.json()["token"])


def mint_key(client, headers):
    response = client.post(KEYS, headers=headers)
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def enrol(client, key, node=NODE):
    return client.post("/providers/enrol", json=node, headers=bearer(key["key"]))


def test_enrolment_key_is_owner_scoped_and_expires_or_revokes(client):
    owner = provider_headers(client)
    other = provider_headers(client, "other@example.test")
    revoked = mint_key(client, owner)
    expired = mint_key(client, owner)
    listed = client.get(KEYS, headers=owner).json()
    assert all("key" not in key and "key_hash" not in key for key in listed)
    assert client.get(KEYS, headers=other).json() == []
    revoke_url = f"{KEYS}/{revoked['enrolment_key_id']}"
    assert client.delete(revoke_url, headers=other).status_code == 404
    assert client.delete(revoke_url, headers=owner).status_code == 204
    assert enrol(client, revoked).status_code == 401
    with db.connect() as conn:
        key_row = conn.execute(
            """
            UPDATE provider_enrolment_keys
            SET expires_at = now() - interval '1 second'
            WHERE enrolment_key_id = %s
            RETURNING key_hash
            """,
            (expired["enrolment_key_id"],),
        ).fetchone()
    assert key_row["key_hash"] == auth.hash_token(expired["key"])
    assert enrol(client, expired).status_code == 401
    assert client.get(NODES, headers=owner).json() == []


def test_simultaneous_redemption_issues_exactly_one_node_credential(client):
    owner = provider_headers(client)
    key = mint_key(client, owner)
    start = Barrier(2, timeout=5)

    def redeem(node):
        start.wait()
        return enrol(client, key, node).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(redeem, (NODE, OTHER_NODE))) == [201, 401]
    assert len(client.get(NODES, headers=owner).json()) == 1


def test_node_ownership_and_registration_recovery(client):
    owner = provider_headers(client)
    other = provider_headers(client, "other@example.test")
    response = enrol(client, mint_key(client, owner))
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    token = bearer(response.json()["node_token"])
    other_key = mint_key(client, other)
    assert enrol(client, other_key).status_code == 409
    assert client.get(NODES, headers=other).json() == []
    other_response = enrol(client, other_key, OTHER_NODE)
    assert other_response.status_code == 201
    assert client.post("/providers/register", json=OTHER_NODE, headers=token).status_code == 401
    assert client.post(
        "/providers/heartbeat", json={**HEARTBEAT, "node_id": OTHER_NODE["node_id"]},
        headers=token,
    ).status_code == 401

    with db.connect() as conn:
        conn.execute("DELETE FROM provider_nodes WHERE node_id = %s", (NODE["node_id"],))
    assert client.post("/providers/heartbeat", json=HEARTBEAT, headers=token).status_code == 404
    assert client.post(
        "/providers/work/claim", params={"node_id": NODE["node_id"]}, headers=token,
    ).status_code == 404
    response = client.post("/providers/register", json=NODE, headers=token)
    assert response.status_code == 200
    assert "node_token" not in response.json()
    node = client.get(NODES, headers=owner).json()[0]
    assert node["hostname"] == "PILOT"
    assert node["inference_eligible"] is node["render_eligible"] is False


def test_legacy_node_can_report_but_cannot_claim_work(client):
    token = "test-legacy-token"
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO provider_nodes (node_id, hostname, node_token_hash, inference_eligible, render_eligible)
            VALUES (%s, 'LEGACY', %s, TRUE, TRUE)
            """,
            (NODE["node_id"], auth.hash_token(token)),
        )
    headers = bearer(token)
    assert client.post("/providers/heartbeat", json=HEARTBEAT, headers=headers).status_code == 200
    assert client.post("/providers/register", json=NODE, headers=headers).status_code == 401
    for queue in ("work", "render"):
        assert client.post(
            f"/providers/{queue}/claim", params={"node_id": NODE["node_id"]}, headers=headers,
        ).status_code == 401


def test_approved_node_claims_and_returns_work_until_revoked(client, monkeypatch):
    monkeypatch.setenv("DISPATCH_WAIT_SEC", "5")
    owner = provider_headers(client)
    other = provider_headers(client, "other@example.test")
    node_result = enrol(client, mint_key(client, owner))
    assert node_result.status_code == 201
    token = bearer(node_result.json()["node_token"])
    params = {"node_id": NODE["node_id"]}
    revoke_url = f"{NODES}/{NODE['node_id']}"
    assert client.post("/providers/heartbeat", json=HEARTBEAT, headers=token).status_code == 200

    customer = client.post("/v1/auth/signup", json={**ACCOUNT, "email": "customer@example.test"})
    assert customer.status_code == 201
    key = client.post(
        "/v1/api-keys", json={}, headers=bearer(customer.json()["token"]),
    ).json()
    customer_api = bearer(key["key"])
    assert client.get("/v1/models", headers=customer_api).status_code == 503

    with db.connect() as conn:
        conn.execute(
            "UPDATE provider_nodes SET inference_eligible = TRUE, render_eligible = TRUE WHERE node_id = %s",
            (NODE["node_id"],),
        )
    assert client.get("/v1/models", headers=customer_api).status_code == 200

    payload = {"model": "fixture:model", "messages": [{"role": "user", "content": "fixture"}]}
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, "/v1/chat/completions", headers=customer_api, json=payload)
        job = None
        deadline = monotonic() + 4
        while job is None and monotonic() < deadline and not pending.done():
            offer = client.post("/providers/work/claim", params=params, headers=token)
            assert offer.status_code == 200
            job = offer.json()["job"]
            if job is None:
                sleep(0.03)
        assert job is not None
        running = client.get(JOBS, headers=owner).json()
        assert len(running) == 1
        assert running[0]["status"] == "claimed"
        assert set(running[0]) == {
            "work_id", "workload", "node_id", "status", "claimed_at", "completed_at",
        }
        result = client.post(
            f"/providers/work/{job['job_id']}/result", params=params, headers=token,
            json={"status": "completed", "content": "synthetic answer"},
        )
        assert result.status_code == 200
        completion = pending.result(timeout=5)
    assert completion.status_code == 200
    assert completion.json()["choices"][0]["message"]["content"] == "synthetic answer"
    finished = client.get(JOBS, headers=owner)
    assert finished.status_code == 200
    assert finished.json()[0]["work_id"] == job["job_id"]
    assert finished.json()[0]["status"] == "completed"
    assert "synthetic answer" not in finished.text
    assert client.get(JOBS, headers=other).json() == []
    assert client.get(JOBS, headers=token).status_code == 401
    assert client.get(JOBS, headers=bearer(customer.json()["token"])).status_code == 401
    assert client.delete(revoke_url, headers=other).status_code == 404
    assert client.delete(revoke_url, headers=owner).status_code == 204
    assert client.delete(revoke_url, headers=owner).status_code == 204
    assert client.get("/v1/models", headers=customer_api).status_code == 503
    assert client.post("/v1/chat/completions", headers=customer_api, json=payload).status_code == 503
    assert client.post("/providers/work/claim", params=params, headers=token).status_code == 401
    assert client.post("/providers/render/claim", params=params, headers=token).status_code == 401
    assert client.post("/providers/register", json=NODE, headers=token).status_code == 401
    assert client.post("/providers/heartbeat", json=HEARTBEAT, headers=token).status_code == 401

    renewed = enrol(client, mint_key(client, owner))
    assert renewed.status_code == 201
    recovered = client.get(NODES, headers=owner).json()[0]
    assert recovered["revoked_at"] is None
    assert recovered["inference_eligible"] is recovered["render_eligible"] is False
    assert client.post("/providers/work/claim", params=params, headers=token).status_code == 401
    assert client.get(JOBS, headers=owner).json() == finished.json()


def test_provider_jobs_follow_the_current_render_claim(client, monkeypatch):
    owner = provider_headers(client)
    other = provider_headers(client, "other@example.test")
    first = enrol(client, mint_key(client, owner), NODE)
    second = enrol(client, mint_key(client, other), OTHER_NODE)
    assert first.status_code == second.status_code == 201
    customer = client.post("/v1/auth/signup", json={**ACCOUNT, "email": "renderer@example.test"})
    assert customer.status_code == 201
    user_id = customer.json()["user"]["user_id"]
    monkeypatch.setattr(main, "_render_storage", lambda: SimpleNamespace(
        presign_get=lambda *args, **kwargs: "https://fixture.invalid/private-source",
        presign_put=lambda *args, **kwargs: "https://fixture.invalid/private-output",
    ))
    with db.connect() as conn:
        conn.execute("UPDATE users SET render_enabled = TRUE WHERE user_id = %s", (user_id,))
        conn.execute(
            """
            UPDATE provider_nodes
            SET render_eligible = TRUE, accepts_work = TRUE, blender_version = '4.3.2',
                last_heartbeat_at = now()
            """
        )
        conn.execute(
            """
            INSERT INTO render_jobs (
                job_id, user_id, status, blender_version, engine, frame_start, frame_end,
                output_format, source_object_key
            ) VALUES ('render-job-fixture', %s, 'queued', '4.3', 'cycles', 1, 2, 'png', 'private-source-key')
            """,
            (user_id,),
        )
        conn.execute(
            """
            INSERT INTO render_frames (frame_id, job_id, frame_number, node_id, status, claimed_at)
            VALUES ('frame-1', 'render-job-fixture', 1, NULL, 'queued', NULL),
                   ('legacy-frame', 'render-job-fixture', 2, %s, 'completed', now())
            """,
            (NODE["node_id"],),
        )
    assert client.get(JOBS, headers=owner).json() == []

    claim = client.post(
        "/providers/render/claim", params={"node_id": NODE["node_id"]},
        headers=bearer(first.json()["node_token"]),
    )
    assert claim.status_code == 200
    assert claim.json()["frame"]["frame_id"] == "frame-1"
    history = client.get(JOBS, headers=owner)
    assert [row["workload"] for row in history.json()] == ["render_frame"]
    assert "private-source" not in history.text and "private-output" not in history.text
    assert "renderer@example.test" not in history.text
    assert client.get(JOBS, headers=other).json() == []

    with db.connect() as conn:
        conn.execute(
            "UPDATE render_frames SET lease_expires_at = now() - interval '1 second' WHERE frame_id = 'frame-1'"
        )
    assert client.get(JOBS, headers=owner).json()[0]["status"] == "lease_expired"

    reclaimed = client.post(
        "/providers/render/claim", params={"node_id": OTHER_NODE["node_id"]},
        headers=bearer(second.json()["node_token"]),
    )
    assert reclaimed.status_code == 200
    assert reclaimed.json()["frame"]["frame_id"] == "frame-1"
    assert client.get(JOBS, headers=owner).json() == []
    assert client.get(JOBS, headers=other).json()[0]["status"] == "claimed"
    with db.connect() as conn:
        conn.execute("UPDATE render_jobs SET status = 'cancelled' WHERE job_id = 'render-job-fixture'")
    assert client.get(JOBS, headers=other).json()[0]["status"] == "cancelled"


def test_operator_approval_is_bound_to_the_current_owner_and_credential(client, monkeypatch):
    provider = provider_headers(client)
    account_id = client.get(f"{PROVIDER_AUTH}/me", headers=provider).json()["provider_account_id"]
    first = enrol(client, mint_key(client, provider))
    assert first.status_code == 201
    credential = bearer(first.json()["node_token"])

    operator_signup = client.post("/v1/auth/signup", json={**ACCOUNT, "email": "operator@example.test"})
    assert operator_signup.status_code == 201
    operator = bearer(operator_signup.json()["token"])
    actor_id = operator_signup.json()["user"]["user_id"]
    approved = {"provider_account_id": account_id, "approved": True}
    assert client.post(APPROVAL, json=approved, headers=provider).status_code == 401
    assert client.post(APPROVAL, json=approved, headers=operator).status_code == 403
    with db.connect() as conn:
        conn.execute("UPDATE users SET is_operator = TRUE WHERE user_id = %s", (actor_id,))
    assert client.post(
        APPROVAL, json={**approved, "provider_account_id": "prv_" + "0" * 32}, headers=operator,
    ).status_code == 404
    assert client.post(APPROVAL, json=approved, headers=operator).status_code == 409
    assert client.post("/providers/heartbeat", json=HEARTBEAT, headers=credential).status_code == 200

    def fail_audit(*args, **kwargs):
        raise psycopg.OperationalError("synthetic audit insert failure")

    with monkeypatch.context() as failure:
        failure.setattr(main, "_record_provider_node_event", fail_audit)
        assert client.post(APPROVAL, json=approved, headers=operator).status_code == 503
    assert client.get(NODES, headers=provider).json()[0]["inference_eligible"] is False
    first_approval = client.post(APPROVAL, json=approved, headers=operator)
    assert first_approval.status_code == 200
    assert first_approval.json()["changed"] is True
    assert client.post(APPROVAL, json=approved, headers=operator).json()["changed"] is False
    machine = client.get(NODES, headers=provider).json()[0]
    assert machine["inference_eligible"] is True and machine["render_eligible"] is False

    with db.connect() as conn:
        conn.execute(
            "UPDATE provider_nodes SET last_heartbeat_at = now() - interval '1 hour' WHERE node_id = %s",
            (NODE["node_id"],),
        )
    pause = {**approved, "approved": False}
    assert client.post(APPROVAL, json=pause, headers=operator).json()["changed"] is True
    assert client.post(APPROVAL, json=approved, headers=operator).status_code == 409

    assert client.post("/providers/heartbeat", json=HEARTBEAT, headers=credential).status_code == 200
    assert enrol(client, mint_key(client, provider)).status_code == 201
    # A fresh timestamp from the earlier credential is insufficient.
    assert client.post(APPROVAL, json=approved, headers=operator).status_code == 409

    revoke_url = f"{NODES}/{NODE['node_id']}"
    with monkeypatch.context() as failure:
        failure.setattr(main, "_record_provider_node_event", fail_audit)
        assert client.delete(revoke_url, headers=provider).status_code == 503
    assert client.get(NODES, headers=provider).json()[0]["revoked_at"] is None
    assert client.delete(revoke_url, headers=provider).status_code == 204
    assert client.delete(revoke_url, headers=provider).status_code == 204
    assert client.post(APPROVAL, json=approved, headers=operator).status_code == 409
    with db.connect() as conn:
        events = conn.execute(
            """
            SELECT event_type, actor_id, provider_account_id
            FROM provider_node_events WHERE node_id = %s ORDER BY event_id
            """,
            (NODE["node_id"],),
        ).fetchall()
    assert [(event["event_type"], event["actor_id"]) for event in events] == [
        ("inference_approved", actor_id), ("inference_paused", actor_id),
        ("node_credential_revoked", account_id),
    ]
    assert {event["provider_account_id"] for event in events} == {account_id}
