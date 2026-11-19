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
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Lowercase hex/alphanumeric with dashes. The agent derives this from stable
# machine facts (see agent/identity.py); the pattern exists so a malformed or
# injected id is rejected at the edge rather than becoming a primary key.
NODE_ID = Field(pattern=r"^[a-z0-9][a-z0-9-]{7,63}$")

# One Ollama model name, e.g. `llama3.1:8b`. Bounded per item, which
# `list[str]` is not: a `max_length` on the list caps how MANY names arrive and
# says nothing about how long each one is, so a caller could send two hundred
# strings of two hundred thousand characters each and every one of them would
# be stored. The list bound and the item bound are different limits and both
# have to be written down.
#
# 200 characters is far above any real name -- the longest in Ollama's library
# is under forty -- and far below anything that makes a row expensive.
MODEL_NAME = Annotated[str, StringConstraints(min_length=1, max_length=200)]


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
    local_models: list[MODEL_NAME] = Field(default_factory=list, max_length=200)

    # The Blender the agent found on this machine, e.g. "4.3.2", or None when
    # there is none. A CAPABILITY REPORT, NOT A PERMISSION: a node saying it has
    # Blender does not make it eligible to render. That is provider_nodes
    # .render_eligible, which defaults FALSE and is only ever set by an
    # operator, because agreeing to execute a stranger's file is a decision the
    # machine's owner makes and not one its software announces.
    #
    # None on every heartbeat from an agent build that predates rendering, which
    # correctly leaves those nodes unmatched rather than guessing a version for
    # them.
    blender_version: str | None = Field(default=None, max_length=32)


class RegisterRequest(Strict):
    node_id: str = NODE_ID
    capability: Capability


class EnrolmentKeyView(BaseModel):
    enrolment_key_id: str
    key_prefix: str
    created_at: datetime
    expires_at: datetime
    redeemed_at: datetime | None
    revoked_at: datetime | None


class EnrolmentKeyCreated(EnrolmentKeyView):
    key: str


class OwnedNodeView(BaseModel):
    node_id: str
    hostname: str | None
    last_heartbeat_at: datetime | None
    accepts_work: bool
    inference_eligible: bool
    render_eligible: bool
    revoked_at: datetime | None
    liveness: str
    gpu_name: str | None
    vram_total_mb: int | None
    gpu_utilisation_pct: int | None
    temperature_c: int | None
    ollama_reachable: bool


class ProviderWorkView(BaseModel):
    work_id: str
    workload: Literal["inference", "render_frame"]
    node_id: str
    status: Literal["claimed", "completed", "failed", "lease_expired", "cancelled"]
    claimed_at: datetime
    completed_at: datetime | None


class InferenceApprovalRequest(Strict):
    provider_account_id: str = Field(pattern=r"^prv_[a-f0-9]{32}$")
    approved: bool = Field(strict=True)


class InferenceApprovalView(BaseModel):
    node_id: str
    provider_account_id: str
    inference_eligible: bool
    changed: bool


class RegisterResponse(BaseModel):
    node_id: str
    registered_at: datetime

    # The server tells the agent how often to check in, rather than the agent
    # deciding. It costs nothing now and means the interval can be changed for
    # the whole fleet later without shipping a new desktop build.
    heartbeat_interval_s: int

    # Issued by enrolment. Authenticated registration only refreshes telemetry.
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


class ProviderAccountView(BaseModel):
    provider_account_id: str
    email: str
    display_name: str | None
    created_at: datetime


class ProviderSessionCreated(BaseModel):
    token: str
    expires_at: datetime
    provider: ProviderAccountView


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


# ---------------------------------------------------------------------------
# RENDERING.
#
# See docs/adr/0006-render-batch-jobs.md. The shape differs from inference in
# one way that drives everything below: the payload is a file, so no request or
# response here ever carries the bytes. They carry presigned URLs, and the
# bytes travel browser -> storage and storage -> provider without passing
# through this process.
#
# The bounds are load-bearing for the same reason they are on Capability and
# Metrics. A frame range is arithmetic a customer controls; without a ceiling,
# `frame_start=1, frame_end=9999999` is a single accepted request that inserts
# ten million rows and hands the fleet a year of work. Pydantic turning that
# into a 422 at the edge is the whole argument for generating this file.
# ---------------------------------------------------------------------------

# The most frames one submission may contain. A ceiling has to exist; this one
# is chosen to be comfortably above a real animation (a 10-second shot at 24fps
# is 240) and far below anything that would fill the queue for weeks.
MAX_FRAMES_PER_JOB = 2_000

# Largest .blend we will mint an upload URL for. Enforced twice: here, against
# the size the client claims, and again by a HEAD against the bucket after the
# upload, against the size the object actually is. The first is a courtesy that
# fails fast; only the second is evidence.
MAX_SOURCE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB

# How many bytes of source one job may cause to be moved across the network in
# total, counting every frame's download.
#
# WHY THIS IS NOT JUST MAX_SOURCE_BYTES. A provider downloads the whole .blend
# once per frame, so a job's real transfer cost is source_bytes multiplied by
# frame count -- and the two existing limits multiply out to 2 GiB x 2,000
# frames, about four terabytes, from a single submission by a single customer.
# Neither limit is wrong on its own; the product of them is what nobody
# bounded. This is the missing third constraint, checked at confirmation time
# when the true source size is finally known.
#
# 256 GiB is roughly a 128 MiB scene rendered as a 2,000-frame animation, or a
# 2 GiB scene at 128 frames. Both are real jobs. What it excludes is the shape
# that is only ever an attack: the largest possible file times the largest
# possible frame count.
MAX_JOB_TRANSFER_BYTES = 256 * 1024 * 1024 * 1024  # 256 GiB

# Bounds on a rendered frame, checked by HEAD after the provider reports
# success. Zero is the one that matters: an empty object is what a provider
# gets by uploading nothing at all, and without a floor it counts as a finished
# frame, completes the job, and is offered to the customer as their render.
MIN_OUTPUT_BYTES = 1
MAX_OUTPUT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB

# The first bytes of a real file in each format we accept, used to check that
# what the provider uploaded is the KIND of thing it claimed to produce.
#
# This is a shape check and not an integrity check, and the difference is worth
# being exact about. It stops a provider handing back a text file, a truncated
# upload, or an HTML error page and having it delivered to the customer as a
# rendered image. It does NOT prove the pixels came from the customer's scene:
# a provider can render anything at all, or send a valid PNG of something else,
# and these eight bytes will not notice. Proving the output corresponds to the
# input needs the sandbox and attestation that ADR 0002 reserves. What this
# closes is the cheapest version of the attack -- upload garbage, get paid --
# and it closes it completely.
OUTPUT_MAGIC: dict[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    # OpenEXR's magic number, 20000630 little-endian. Both orderings are listed
    # because the specification fixes the value and not the file's endianness.
    "exr": (b"\x76\x2f\x31\x01", b"\x01\x31\x2f\x76"),
}

# How many bytes to fetch to perform that check. The longest magic above is
# eight; sixteen is fetched so a format added later does not silently start
# comparing against a short read.
OUTPUT_MAGIC_BYTES = 16

# `4.3`, `4.2.1`. Matched against provider_nodes.blender_version at claim time,
# so a value no node has simply means no node claims it.
BLENDER_VERSION = Field(pattern=r"^\d{1,2}\.\d{1,2}(\.\d{1,2})?$")


class RenderJobCreateRequest(Strict):
    """A submission. Returns an upload URL; it does not carry the file."""

    blender_version: str = BLENDER_VERSION

    # Cycles is path-traced and GPU-bound; EEVEE is rasterised and much faster.
    # Both are Blender built-ins, so neither needs anything installed beyond
    # Blender itself.
    engine: Literal["cycles", "eevee"]

    # Blender's own frame numbering. Zero is legal; negatives are not.
    frame_start: int = Field(ge=0, le=1_048_574)
    frame_end: int = Field(ge=0, le=1_048_574)

    # No mp4. Muxing frames into a video is a step that runs after every frame
    # lands, and nothing performs it. Accepting the format and delivering
    # stills would be the silent kind of wrong; rejecting it is the loud kind.
    output_format: Literal["png", "exr"]

    # What the client says it is about to upload, used to refuse an obviously
    # oversized job before a URL is minted. Verified after the fact.
    source_bytes: int = Field(ge=1, le=MAX_SOURCE_BYTES)

    # The customer's stated ceiling. Recorded, not enforced -- there is no
    # metering to enforce it against. See render_jobs.spending_limit_usd.
    spending_limit_usd: float | None = Field(default=None, ge=0, le=100_000)

    @field_validator("frame_end")
    @classmethod
    def _range_is_sane(cls, value: int, info):
        start = info.data.get("frame_start")
        if start is None:
            # frame_start already failed its own validation; reporting a second
            # error about a field we could not read would just be noise.
            return value
        if value < start:
            raise ValueError("frame_end must not be less than frame_start")
        if value - start + 1 > MAX_FRAMES_PER_JOB:
            raise ValueError(
                f"a job may contain at most {MAX_FRAMES_PER_JOB} frames; "
                f"this range is {value - start + 1}"
            )
        return value


class RenderJobCreated(BaseModel):
    """Where to PUT the file, and for how long that is possible.

    `upload_expires_at` is returned rather than left implicit because a large
    upload over a domestic connection can outlive a short-lived URL. A client
    that knows the deadline can warn or re-request; a client that does not
    discovers it as an opaque 403 at ninety percent.
    """

    job_id: str
    status: str
    frame_count: int
    upload_url: str
    upload_expires_at: datetime


class RenderFrameView(BaseModel):
    """One frame's state, as the customer sees it."""

    frame_number: int
    status: str
    attempts: int
    render_seconds: float | None = None
    error_code: str | None = None
    completed_at: datetime | None = None


class RenderJobView(BaseModel):
    """A job's state.

    `status` here is DERIVED from the frames on every read and is not the
    column of the same name in render_jobs -- see the comment above the table.
    The counts are returned alongside it because "running" on its own tells a
    customer nothing about whether to keep the tab open.
    """

    job_id: str
    status: str
    blender_version: str
    engine: str
    frame_start: int
    frame_end: int
    output_format: str
    frame_count: int
    frames_completed: int
    frames_failed: int
    frames_running: int
    spending_limit_usd: float | None = None
    source_bytes: int | None = None
    error_code: str | None = None
    created_at: datetime
    uploaded_at: datetime | None = None

    # Populated on the detail view only. A list endpoint returning every frame
    # of every job would be a megabyte of JSON to render a progress bar.
    frames: list[RenderFrameView] | None = None


class RenderJobList(BaseModel):
    jobs: list[RenderJobView]


class RenderArtifact(BaseModel):
    """One finished frame, and a short-lived URL to fetch it with."""

    frame_number: int
    url: str
    bytes: int | None = None


class RenderArtifactList(BaseModel):
    job_id: str
    artifacts: list[RenderArtifact]
    expires_at: datetime


# ---------------------------------------------------------------------------
# The provider half.
# ---------------------------------------------------------------------------


class RenderFrameOffer(BaseModel):
    """One claimed frame, handed to exactly one agent.

    Both URLs are presigned, single-object, and expire inside the lease. That
    is the whole of the provider's access to storage: it can read this one
    .blend and write this one output. It cannot list the bucket, read another
    customer's project, or overwrite a frame that is already finished.

    No storage credential appears here, and none is ever sent to an agent.
    A credential that never reaches a machine cannot leak from it.
    """

    frame_id: str
    job_id: str
    frame_number: int

    blender_version: str
    engine: str
    output_format: str

    source_url: str
    output_url: str

    lease_expires_at: datetime


class RenderClaimResponse(BaseModel):
    """Either a frame, or nothing to do. Same shape as JobClaimResponse."""

    frame: RenderFrameOffer | None = None
    poll_interval_s: int


class RenderResultRequest(Strict):
    """The agent reporting what happened to one frame. Terminal either way."""

    # 'completed' or 'failed'. Not a Literal, for the same reason
    # JobResultRequest.status is not one: an agent build newer than this
    # orchestrator must have its report recorded rather than rejected, or the
    # frame sits until its lease lapses and the work is simply done again.
    status: str = Field(min_length=1, max_length=32)

    # What the agent uploaded, as it measured it. Cross-checked against the
    # object in the bucket before the frame is accepted as completed -- an
    # agent that reports success without uploading anything is the failure this
    # check exists for, and it is not hypothetical: a crash between render and
    # upload produces exactly that report.
    output_bytes: int | None = Field(default=None, ge=0)

    # Wall-clock, as measured by the agent. EVIDENCE, NOT A BILL. Turning this
    # into an amount owed is metering, hand-built under ADR 0002, and
    # agent/core/meter.py still raises NotImplementedError. Nothing downstream
    # should read this as settled.
    render_seconds: float | None = Field(default=None, ge=0, le=86_400)

    error_code: str | None = Field(default=None, max_length=64)


class RenderResultAccepted(BaseModel):
    frame_id: str
    status: str
