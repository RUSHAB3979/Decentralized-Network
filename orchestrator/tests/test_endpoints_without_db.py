"""The failure path, which is the half that normally goes untested.

CI has no Postgres, so these tests cannot check that a heartbeat is stored.
What they can check is the behaviour that actually gets exercised in an
incident: what every endpoint does when the database is unreachable. That path
has to be right, because the agent's retry logic is built on it -- a 503 means
"try again", and anything else means "stop".
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orchestrator.main import app, heartbeat_interval_s, ttl

NODE_ID = "a1b2c3d4e5f6a7b8"
CAPABILITY = {"hostname": "DESKTOP-TEST", "logical_cores": 16}


@pytest.fixture
def client(monkeypatch):
    """A client with no database configured.

    DATABASE_URL is removed rather than pointed at a dead host: an unroutable
    address would make every test wait out a five-second connect timeout, and
    slow tests get deleted. The code path is the same either way -- both raise
    before any query runs.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as c:
        yield c


def test_service_endpoint_does_not_need_the_database(client):
    # Liveness of the process itself, distinct from readiness. A load balancer
    # must be able to tell "this instance is running" from "this instance can
    # serve traffic", or a database blip restarts every orchestrator at once.
    response = client.get("/service")
    assert response.status_code == 200
    assert response.json() == {"service": "orchestrator"}


def test_health_reports_degraded_rather_than_crashing(client):
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["db"] == "down"


def test_register_returns_503_not_500(client):
    # 503 is retryable and 500 is a bug. The agent treats them differently, so
    # getting this wrong either hides a real defect or makes a transient
    # outage permanently deregister a node.
    response = client.post(
        "/providers/register", json={"node_id": NODE_ID, "capability": CAPABILITY}
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_heartbeat_returns_503_not_500(client):
    response = client.post(
        "/providers/heartbeat", json={"node_id": NODE_ID, "status": "idle"}
    )
    assert response.status_code == 503


def test_node_list_returns_503_not_an_empty_list(client):
    # The important one. An empty list means "no providers have enrolled";
    # a 503 means "we cannot currently tell". If the database being down
    # rendered as an empty marketplace, the website would confidently show
    # zero capacity during an outage and nobody would know why.
    #
    # A token is sent because the endpoint now requires a session. It is not a
    # real one and does not need to be: with no database the session lookup
    # cannot complete either, so this still lands on the 503 path. The point of
    # sending it is to prove the outage is still reported as an outage after
    # the endpoint was closed -- an unauthenticated 401 here would pass a
    # weaker test while telling the console the wrong thing.
    response = client.get(
        "/providers/nodes", headers={"Authorization": "Bearer nf_sess_notreal"}
    )
    assert response.status_code == 503


def test_node_list_refuses_anonymous_callers(client):
    # The registry describes real machines belonging to real providers:
    # hostname, GPU, driver version, installed models, and when they are awake.
    # It was served anonymously until 2026-08-16. This test exists so that
    # reverting the gate is a red build rather than a quiet regression.
    #
    # 401 arrives before any database work, which is why this passes with no
    # DATABASE_URL set at all.
    response = client.get("/providers/nodes")
    assert response.status_code == 401


SIGNUP = {"email": "someone@example.com", "password": "a-long-enough-password"}


def test_signup_is_refused_when_signups_are_closed(client, monkeypatch):
    # 403, not 404 and not 503. The caller cannot fix this by retrying and the
    # endpoint is not broken, so the response has to say which of those it is.
    monkeypatch.setenv("SIGNUPS_OPEN", "false")
    response = client.post("/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 403
    assert "closed" in response.json()["detail"]


def test_closed_signup_refuses_before_touching_the_database(client, monkeypatch):
    # There is no DATABASE_URL in this fixture, so a 503 here would prove the
    # refusal happens after the database work rather than before it. That
    # ordering is the whole defence: scrypt is deliberately slow, and hashing
    # first would let anyone spend our CPU against a door we have shut.
    monkeypatch.setenv("SIGNUPS_OPEN", "false")
    assert client.post("/v1/auth/signup", json=SIGNUP).status_code == 403


def test_signup_still_works_normally_when_open(client, monkeypatch):
    # 503 rather than 403: the flag is not blocking, and the request got as far
    # as needing a database. Without this test, a bug that closed signup
    # permanently would look exactly like the feature working.
    monkeypatch.setenv("SIGNUPS_OPEN", "true")
    assert client.post("/v1/auth/signup", json=SIGNUP).status_code == 503


def test_an_unrecognised_flag_value_leaves_signups_open(client, monkeypatch):
    # Fail open on a typo. Someone setting SIGNUPS_OPEN=flase must not
    # discover it by finding nobody can register, with no error anywhere to
    # explain why. Closing the door is meant to be a deliberate act.
    monkeypatch.setenv("SIGNUPS_OPEN", "flase")
    assert client.post("/v1/auth/signup", json=SIGNUP).status_code == 503


def test_validation_runs_before_the_database_is_touched(client):
    # A malformed request is rejected with 422 even with no database at all.
    # If this returned 503 it would mean bad payloads were reaching storage
    # whenever the database happened to be up.
    response = client.post(
        "/providers/register", json={"node_id": "bad id", "capability": CAPABILITY}
    )
    assert response.status_code == 422


def test_ttl_is_comfortably_longer_than_the_heartbeat_interval():
    # The invariant that keeps the fleet from flapping. If TTL ever drops
    # below the interval, every node goes offline between its own heartbeats,
    # and nothing in the system would raise -- the marketplace would just
    # appear empty. Three intervals leaves room for two dropped requests.
    assert ttl().total_seconds() >= heartbeat_interval_s() * 3


# ---------------------------------------------------------------------------
# Accounts and the work queue, with no database.
#
# Same principle as the tests above: CI cannot prove a user was stored, but it
# can prove what every new endpoint does when storage is gone. These paths run
# during an incident, and the agent's retry loop is built on the codes they
# return.
# ---------------------------------------------------------------------------

SIGNUP = {"email": "provider@example.com", "password": "a-long-enough-password"}


def test_signup_returns_503_not_500(client):
    response = client.post("/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 503


def test_login_returns_503_not_500(client):
    response = client.post("/v1/auth/login", json=SIGNUP)
    assert response.status_code == 503


def test_signup_validates_before_touching_storage(client):
    # A short password must be a 422 even with no database at all. If this were
    # a 503, it would mean weak passwords were reaching the hasher and the table
    # whenever Postgres happened to be up.
    response = client.post(
        "/v1/auth/signup", json={"email": "a@b.co", "password": "short"}
    )
    assert response.status_code == 422


def test_signup_rejects_a_malformed_email_before_storage(client):
    response = client.post(
        "/v1/auth/signup", json={"email": "not-an-email", "password": "a-long-password"}
    )
    assert response.status_code == 422


def test_authenticated_endpoints_reject_a_missing_header_before_storage(client):
    # 401 rather than 503: the request is unauthenticated regardless of whether
    # the database is reachable, and answering 503 would tell an anonymous
    # caller about our infrastructure.
    assert client.get("/v1/auth/me").status_code == 401
    assert client.get("/v1/api-keys").status_code == 401
    assert client.post("/v1/api-keys", json={"name": "k"}).status_code == 401


def test_work_endpoints_reject_a_missing_credential_before_storage(client):
    claim = client.post("/providers/work/claim", params={"node_id": NODE_ID})
    assert claim.status_code == 401

    result = client.post(
        f"/providers/work/{'job_x'}/result",
        params={"node_id": NODE_ID},
        json={"status": "completed"},
    )
    assert result.status_code == 401


def test_chat_completions_rejects_a_missing_key_before_storage(client):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 401


def test_streaming_is_refused_before_authentication(client):
    # Cheapest possible rejection of something we cannot do. Checked before the
    # key lookup so an unsupported request never costs a database round trip.
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer nf_demo_whatever"},
        json={
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert response.status_code == 400


def test_job_lease_outlives_the_claim_wait():
    # If a lease could expire while an agent was still holding the claim open,
    # work would be reassigned to a second provider before the first had a
    # chance to start it -- and the customer would pay for two runs of one
    # request. Nothing would raise; the bill would simply be wrong.
    from orchestrator.main import claim_poll_interval_s, job_lease_s

    assert job_lease_s() > claim_poll_interval_s()


def test_dispatch_wait_outlives_a_single_claim_cycle():
    # The customer must not be given up on faster than an idle agent can come
    # back and take the job.
    from orchestrator.main import claim_poll_interval_s, dispatch_wait_s

    assert dispatch_wait_s() > claim_poll_interval_s()
