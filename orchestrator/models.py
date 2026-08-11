"""The wire contract between the provider agent and the orchestrator.

tasks.md M1 item 2 marks this "ships first", and the ordering is the point: the
agent (R6) and the endpoints (R5) are written by different people at the same
time, so the only thing keeping them compatible is this file. Anything not
described here is not part of the contract.

The split into Capability and Metrics is not cosmetic. Capability is what the
machine *is* -- GPU, RAM, cores -- and it changes when hardware or drivers
change, so it is sent at registration. Metrics are what the machine is *doing*,
and they are sent on every heartbeat. Keeping them apart means the frequent
message stays small, and it stops a heartbeat from silently rewriting hardware
facts that scheduling decisions were made against.

On validation: the constraints below are load-bearing, not decoration. A
percentage outside 0-100 or a negative VRAM figure means the agent's detection
went wrong -- nvidia-smi printing '[N/A]', a parse landing on the wrong CSV
column -- and without a bound those values reach the database, the website
renders "-4% utilised", and nothing raises. Per ADR 0002 this is generated code
precisely because Pydantic turns that class of silent corruption into a loud
422 at the edge.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Lowercase hex/alphanumeric with dashes. The agent derives this from stable
# machine facts (see agent/identity.py); the pattern exists so a malformed or
# injected id is rejected at the edge rather than becoming a primary key.
NODE_ID = Field(pattern=r"^[a-z0-9][a-z0-9-]{7,63}$")


class Strict(BaseModel):
    """Base for every request model: unknown fields are an error, not noise.

    Pydantic's default is to ignore fields it does not recognise. That turns a
    renamed field into silence -- the agent sends `vram_used`, the orchestrator
    wants `vram_used_mb`, the request succeeds, and the column is simply never
    populated. Forbidding extras makes a contract drift fail immediately, on
    the first heartbeat, with the wrong field named in the response.
    """

    model_config = ConfigDict(extra="forbid")


class Capability(Strict):
    """What this machine is. Sent at registration."""

    hostname: str = Field(min_length=1, max_length=255)
    os_version: str | None = Field(default=None, max_length=255)
    cpu: str | None = Field(default=None, max_length=255)
    logical_cores: int | None = Field(default=None, ge=0, le=4096)
    ram_total_mb: int | None = Field(default=None, ge=0)

    # All None on a machine with no NVIDIA GPU. That is a normal, expected
    # provider -- someone installed the app on a laptop -- and it must register
    # successfully so the dashboard can tell them why they cannot earn yet.
    gpu_name: str | None = Field(default=None, max_length=255)
    vram_total_mb: int | None = Field(default=None, ge=0)
    gpu_driver: str | None = Field(default=None, max_length=64)

    agent_version: str | None = Field(default=None, max_length=32)


class Metrics(Strict):
    """What this machine is doing right now. Sent on every heartbeat."""

    gpu_utilisation_pct: int | None = Field(default=None, ge=0, le=100)
    vram_used_mb: int | None = Field(default=None, ge=0)
    temperature_c: int | None = Field(default=None, ge=-50, le=150)

    ollama_reachable: bool = False
    ollama_version: str | None = Field(default=None, max_length=64)

    # Models resident on this machine's disk. The agent filters Ollama Cloud
    # entries out before sending: those are pointers to ollama.com, not local
    # weights, and a node that advertised them would be offering capacity it
    # does not have. The cap is a payload bound, not a product limit.
    local_models: list[str] = Field(default_factory=list, max_length=200)


class RegisterRequest(Strict):
    node_id: str = NODE_ID
    capability: Capability


class RegisterResponse(BaseModel):
    node_id: str
    registered_at: datetime

    # The server tells the agent how often to check in, rather than the agent
    # deciding. It costs nothing now and means the interval can be changed for
    # the whole fleet later without shipping a new desktop build.
    heartbeat_interval_s: int


class HeartbeatRequest(Strict):
    node_id: str = NODE_ID

    # The agent's own view of itself, mirroring agent/state.py's Status enum.
    # Not constrained to that enum here: the orchestrator storing a status it
    # does not recognise is harmless, whereas rejecting heartbeats from a
    # slightly newer agent build would take working nodes offline on deploy.
    status: str = Field(min_length=1, max_length=32)
    detail: str = Field(default="", max_length=512)
    accepts_work: bool = False
    metrics: Metrics = Field(default_factory=Metrics)


class HeartbeatResponse(BaseModel):
    node_id: str
    received_at: datetime
    heartbeat_interval_s: int


class NodeView(BaseModel):
    """One row as the website renders it.

    Separate from the storage shape on purpose. This is the model that will
    eventually be filtered for what a customer is allowed to see, and having
    the seam already there means that change is a diff in one file rather than
    an audit of every query.
    """

    node_id: str
    hostname: str
    liveness: str  # 'online' | 'offline' | 'never_seen' -- see liveness.py
    status: str | None
    detail: str | None
    accepts_work: bool

    gpu_name: str | None
    vram_total_mb: int | None
    vram_used_mb: int | None
    gpu_driver: str | None
    gpu_utilisation_pct: int | None
    temperature_c: int | None

    cpu: str | None
    logical_cores: int | None
    ram_total_mb: int | None
    os_version: str | None
    agent_version: str | None

    ollama_reachable: bool
    ollama_version: str | None
    local_models: list[str]

    registered_at: datetime
    last_heartbeat_at: datetime | None


class NodeList(BaseModel):
    nodes: list[NodeView]

    # Echoed so the frontend can render "offline after 120s" without hardcoding
    # a number that only exists in the orchestrator's environment.
    ttl_seconds: int
    server_time: datetime
