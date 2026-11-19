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

from orchestrator import main
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
        "/providers/register",
        json={"node_id": NODE_ID, "capability": CAPABILITY},
        headers={"Authorization": "Bearer enrolled-node-fixture"},
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_register_refuses_to_issue_an_anonymous_credential(client):
    response = client.post(
        "/providers/register", json={"node_id": NODE_ID, "capability": CAPABILITY}
    )
    assert response.status_code == 401


def test_heartbeat_returns_503_not_500(client):
    # A credential is sent for the same reason the node-list test below sends
    # one: the heartbeat is authenticated now, and without a token this would
    # pass as a 401 while proving nothing about the outage path. The token is
    # not real and does not have to be -- with no database the node lookup
    # cannot complete, which is exactly the case under test.
    response = client.post(
        "/providers/heartbeat",
        json={"node_id": NODE_ID, "status": "idle"},
        headers={"Authorization": "Bearer not-a-real-node-token"},
    )
    assert response.status_code == 503


def test_heartbeat_without_a_credential_is_refused(client):
    """node_id is public; the right to speak for it is not.

    It is printed in the agent's logs and returned in the marketplace listing,
    so before the heartbeat was authenticated, knowing one was enough to post
    telemetry as that machine -- hold a dead node visible, mark a busy one
    idle, or advertise models it does not have. The refusal is checked here
    rather than in a database test because it must not depend on the database
    being up: it is decided from the request alone.
    """
    response = client.post(
        "/providers/heartbeat", json={"node_id": NODE_ID, "status": "idle"}
    )
    assert response.status_code == 401


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


# -- admission control ------------------------------------------------------


def test_repeated_signups_are_rate_limited_before_the_password_is_hashed(client):
    """scrypt is a lever, and an unauthenticated caller must not hold it.

    The KDF is deliberately slow and memory-hungry -- roughly 16 MiB and real
    CPU per call. On a 512 MB instance a few dozen concurrent signups for
    addresses that do not exist saturate the machine, and every other endpoint
    stops answering. Rate limiting is the only defence available here, because
    the whole point of a signup is that the caller has proved nothing yet.

    The refusal is asserted to arrive with a Retry-After: a 429 without one
    tells the client to back off by an amount it has to guess, and clients that
    guess badly retry immediately.
    """
    seen = [
        client.post("/v1/auth/signup", json=SIGNUP).status_code for _ in range(12)
    ]
    assert 429 in seen, seen

    refused = client.post("/v1/auth/signup", json=SIGNUP)
    assert refused.status_code == 429
    assert int(refused.headers["Retry-After"]) >= 1


def test_logins_are_limited_per_account_as_well_as_per_caller(client, monkeypatch):
    """One limiter is not enough, and the two answer different attacks.

    A per-caller limit alone leaves a distributed guessing run against one known
    address free to try thousands of passwords for it, every source staying
    comfortably inside its own allowance. A per-account limit alone lets one
    caller work through a list of addresses at full speed.
    """
    from orchestrator import limits

    # Stand in for a distributed run: the per-caller limiter is made permissive
    # so that the only thing left to refuse these attempts is the per-account
    # one. Real attackers achieve the same effect with more addresses.
    monkeypatch.setattr(limits, "auth_by_address", limits.RateLimiter(10_000, 60))

    seen = []
    for _ in range(limits.auth_by_account.limit + 2):
        seen.append(
            client.post(
                "/v1/auth/login",
                json={"email": "victim@example.com", "password": "x" * 12},
            ).status_code
        )
    assert 429 in seen, seen

    # And the address is normalised before it is counted, so changing the
    # capitalisation is not a fresh budget.
    response = client.post(
        "/v1/auth/login", json={"email": "VICTIM@example.com", "password": "x" * 12}
    )
    assert response.status_code == 429


def test_a_rate_limited_caller_is_refused_without_reaching_the_database(client):
    # Ordering, stated as a test. If the limit were applied after the lookup,
    # every refused attempt would still cost a connection -- and under the load
    # this exists to survive, connections are the resource that runs out first.
    for _ in range(20):
        client.post("/v1/auth/login", json={"email": "a@b.co", "password": "x" * 12})

    response = client.post(
        "/v1/auth/login", json={"email": "a@b.co", "password": "x" * 12}
    )
    assert response.status_code == 429
    assert "unavailable" not in response.json()["detail"].lower()


# -- security headers -------------------------------------------------------


def test_every_response_carries_the_security_headers(client):
    """Including the ones no handler wrote.

    These are set as middleware rather than per-route precisely so that a 422
    from validation, a 404 for a path that does not exist, and a 500 from an
    unhandled exception are covered too -- the responses a per-route decorator
    would miss are the ones most likely to reflect input back at a browser.
    """
    for response in (
        client.get("/service"),
        client.get("/health"),
        client.get("/no-such-path"),
        client.post("/v1/auth/signup", json={"email": "bad", "password": "short"}),
    ):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cache-Control"] == "no-store"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_the_documentation_page_is_exempt_from_the_content_policy(client):
    """A policy that breaks /docs would be quietly reverted by whoever hit it.

    Swagger UI loads its assets from a CDN, so default-src 'none' leaves an
    empty frame that loads forever. The rest of the headers still apply -- only
    the content policy is lifted, and only here.
    """
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return {"?column?": 1}


class _FakeConn:
    """Answers SELECT 1 and nothing else. Reachable, which is the whole point.

    It accepts commit() because the lifespan handler runs apply_schema() over
    this same fake on TestClient entry. Accepting the write is what lets the
    test then set the flag by hand and describe the state that matters: a
    database this process can talk to, holding a schema it cannot use.
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return _FakeCursor()

    def commit(self):
        return None


def test_health_is_degraded_when_the_schema_did_not_apply(monkeypatch):
    """A reachable database is not a usable one.

    schema.sql runs as one statement in one transaction, so a single bad
    statement rolls the whole file back and the ADD COLUMNs never land. The
    process then boots and 503s every authenticated request while SELECT 1
    keeps succeeding. Reporting that as "ok" is how such a deploy survives in
    production unnoticed, which is exactly what happened once already.
    """
    monkeypatch.setattr(main.db, "connect", lambda: _FakeConn())
    failure = 'UndefinedTable: relation "render_jobs" does not exist'

    with TestClient(app) as client:
        # Set inside the context: the lifespan handler runs on entry and would
        # otherwise overwrite it. This is the state a real deploy is left in.
        monkeypatch.setattr(main, "_schema_error", failure)
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] == "ok"
    assert body["schema"] == "not applied"
    # The class name, not the statement text: /health is unauthenticated.
    assert body["error"] == "UndefinedTable"
    assert "render_jobs" not in response.text


def test_health_is_ok_only_when_the_schema_applied(monkeypatch):
    monkeypatch.setattr(main.db, "connect", lambda: _FakeConn())

    with TestClient(app) as client:
        monkeypatch.setattr(main, "_schema_error", None)
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["schema"] == "ok"
