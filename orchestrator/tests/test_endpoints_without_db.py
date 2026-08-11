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
    response = client.get("/providers/nodes")
    assert response.status_code == 503


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
