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
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    # The node's transport credential, returned exactly once per registration
    # and never readable again. The agent persists it and presents it when
    # claiming work; the orchestrator keeps only a digest.
    #
    # Optional so that a newer agent talking to an orchestrator that predates
    # this field does not fail to parse the response. An agent that gets None
    # here simply cannot claim work, which is the honest degradation.
    node_token: str | None = None


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


class ApiKeyCreateRequest(Strict):
    name: str = Field(default="Local demo key", min_length=1, max_length=80)


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    created_at: datetime


class ApiKeyView(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyList(BaseModel):
    keys: list[ApiKeyView]


class ChatMessage(Strict):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32_000)


class ChatCompletionRequest(Strict):
    model: str = Field(min_length=1, max_length=255)
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    stream: bool = False


class ChatCompletionMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: str


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatUsage


class ModelView(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "nodeforge-provider"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelView]


class UsageSummary(BaseModel):
    requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_duration_ms: int


# ---------------------------------------------------------------------------
# Accounts.
#
# Signup and login carry a password, so these models are the last place it is
# a plain string before orchestrator/auth.py turns it into a digest. Nothing
# below is ever echoed back: there is no response model here with a password
# field, which is the cheapest way to guarantee one never reaches a log or a
# browser.
# ---------------------------------------------------------------------------


class _EmailNormalising(Strict):
    """Trim and lowercase an email before anything else looks at it.

    `mode="before"` matters: it runs ahead of the pattern check. Validating
    first and normalising later means a trailing space -- which phone keyboards
    add on their own after autocomplete -- is a 422 telling someone their own
    email address is malformed. Normalising first also guarantees the value the
    UNIQUE constraint sees is the same value a later login looks up, so one
    person cannot become two accounts.
    """

    # check_fields=False because this base class declares no `email` field
    # itself -- its subclasses do. Without it Pydantic refuses to build the
    # class, on the reasonable grounds that a validator naming a field that does
    # not exist is usually a typo.
    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def _normalise_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class SignupRequest(_EmailNormalising):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    # Minimum 10 rather than the customary 8. Length is the only property that
    # reliably resists an offline wordlist; composition rules ("one capital,
    # one symbol") mostly produce Password1! and a person who cannot remember
    # it. The upper bound exists because scrypt hashes whatever it is given,
    # and a megabyte-long password is a free way to burn server CPU.
    password: str = Field(min_length=10, max_length=256)

    display_name: str | None = Field(default=None, max_length=80)


class LoginRequest(_EmailNormalising):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserView(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    created_at: datetime


class SessionCreated(BaseModel):
    # Returned exactly once, at signup and login. The server keeps only a
    # digest, so this value cannot be re-read afterwards -- losing it means
    # logging in again, not recovering it.
    token: str
    expires_at: datetime
    user: UserView


# ---------------------------------------------------------------------------
# The provider work queue.
#
# These are the agent's half of the contract, and they are separate from the
# customer-facing chat models on purpose. A customer sends OpenAI-shaped
# messages; an agent receives a job envelope. Collapsing the two would mean the
# request format a customer controls is the format an agent executes, with no
# seam to validate or rewrite at.
# ---------------------------------------------------------------------------


class JobPayload(BaseModel):
    """What the agent is being asked to run."""

    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None


class JobOffer(BaseModel):
    """One claimed job, handed to exactly one agent."""

    job_id: str
    model: str
    payload: JobPayload

    # When this claim lapses and the job becomes claimable again. Sent so the
    # agent can abandon work it can no longer deliver, rather than finishing a
    # job whose lease expired and whose result will be rejected.
    lease_expires_at: datetime


class JobClaimResponse(BaseModel):
    """Either a job, or nothing to do.

    `job` is nullable rather than the endpoint returning 204, because the agent
    long-polls: an empty result is a normal, frequent, successful outcome and
    modelling it as a body keeps the client's parsing identical either way.
    """

    job: JobOffer | None = None

    # Echoed so the agent can pace itself from the server rather than from a
    # constant compiled into a desktop build that ships on its own schedule.
    poll_interval_s: int


class JobResultRequest(Strict):
    """The agent reporting what happened. Terminal either way."""

    # 'completed' or 'failed'. Not a Literal: an agent build newer than this
    # orchestrator reporting an unrecognised terminal state should be recorded,
    # not rejected -- rejecting it would strand the job until its lease lapsed
    # and then run the work a second time.
    status: str = Field(min_length=1, max_length=32)

    content: str = Field(default="", max_length=1_000_000)
    finish_reason: str = Field(default="stop", max_length=32)

    # Counted by the runtime, reported as evidence. NOT a billing figure.
    # Turning these into money is metering, which is hand-built under ADR 0002
    # and lives in agent/core/meter.py -- currently NotImplementedError. The
    # bounds are sanity limits on a number parsed out of another process's
    # JSON, in the same spirit as the GPU metrics above.
    prompt_tokens: int = Field(default=0, ge=0, le=10_000_000)
    completion_tokens: int = Field(default=0, ge=0, le=10_000_000)
    total_duration_ms: int | None = Field(default=None, ge=0)

    error_code: str | None = Field(default=None, max_length=64)


class JobResultAccepted(BaseModel):
    job_id: str
    status: str
