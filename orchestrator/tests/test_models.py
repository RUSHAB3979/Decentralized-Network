"""The wire contract's guard rails.

Every test here is a defect that would otherwise be silent: a bad value reaches
the database, the website renders it, and no exception is raised anywhere. That
is the whole reason the models carry constraints instead of bare types.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from orchestrator.models import (
    Capability,
    ChatCompletionRequest,
    HeartbeatRequest,
    Metrics,
    RegisterRequest,
)

NODE_ID = "a1b2c3d4e5f6a7b8"


def capability(**overrides) -> dict:
    base = {"hostname": "DESKTOP-TEST", "logical_cores": 16, "ram_total_mb": 32768}
    base.update(overrides)
    return base


def test_minimal_registration_is_accepted():
    req = RegisterRequest(node_id=NODE_ID, capability=capability())
    assert req.capability.gpu_name is None


def test_machine_with_no_gpu_can_register():
    # A laptop with no NVIDIA card is a real provider who installed the app.
    # It must enrol successfully so the dashboard can explain why it cannot
    # earn yet, rather than failing at the edge with a validation error.
    req = RegisterRequest(node_id=NODE_ID, capability=capability(gpu_name=None))
    assert req.capability.hostname == "DESKTOP-TEST"


@pytest.mark.parametrize(
    "node_id",
    [
        "short",  # under the minimum length
        "UPPERCASE-ID-1234",  # case is not part of the alphabet
        "has spaces here!",
        "-leading-dash-1234",
        "",
        "x" * 128,  # over the maximum length
    ],
)
def test_malformed_node_ids_are_rejected(node_id):
    with pytest.raises(ValidationError):
        RegisterRequest(node_id=node_id, capability=capability())


def test_unknown_fields_are_rejected():
    # Contract drift, e.g. the agent sending `vram_used` where the orchestrator
    # expects `vram_used_mb`. Pydantic's default would ignore it and leave the
    # column empty forever; extra="forbid" turns it into a 422 on heartbeat one.
    with pytest.raises(ValidationError):
        RegisterRequest(
            node_id=NODE_ID, capability=capability(gpu_vram="24GB")
        )


@pytest.mark.parametrize("pct", [-1, 101, 4294967295])
def test_impossible_gpu_utilisation_is_rejected(pct):
    # nvidia-smi prints '[N/A]' for unsupported fields and a mis-indexed CSV
    # parse lands values in the wrong column. Either produces a number that is
    # not a percentage, and without this bound it renders on the website.
    with pytest.raises(ValidationError):
        Metrics(gpu_utilisation_pct=pct)


def test_absent_gpu_metrics_are_allowed():
    m = Metrics()
    assert m.gpu_utilisation_pct is None
    assert m.ollama_reachable is False
    assert m.local_models == []


@pytest.mark.parametrize("value", [-1, -4096])
def test_negative_memory_is_rejected(value):
    with pytest.raises(ValidationError):
        Metrics(vram_used_mb=value)
    with pytest.raises(ValidationError):
        Capability(hostname="h", ram_total_mb=value)


def test_model_list_is_bounded():
    with pytest.raises(ValidationError):
        Metrics(local_models=[f"model-{i}" for i in range(201)])


def test_heartbeat_defaults_to_not_accepting_work():
    # The safe default. A heartbeat that omitted the field must never be read
    # as "this node is ready for paid work"; scheduling would send it a lease
    # it cannot serve.
    hb = HeartbeatRequest(node_id=NODE_ID, status="idle")
    assert hb.accepts_work is False
    assert hb.metrics.ollama_reachable is False


def test_unrecognised_status_string_is_accepted():
    # Deliberately not constrained to agent/state.py's enum. A newer agent
    # build reporting a status this orchestrator has not heard of should keep
    # heartbeating, not be taken offline by a deploy ordering accident.
    hb = HeartbeatRequest(node_id=NODE_ID, status="reprovisioning")
    assert hb.status == "reprovisioning"


def test_chat_contract_accepts_an_openai_style_request():
    request = ChatCompletionRequest(
        model="tinyllama:latest",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=64,
    )
    assert request.messages[0].role == "user"
    assert request.stream is False


def test_chat_contract_rejects_unbounded_output():
    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            model="tinyllama:latest",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1_000_000,
        )
