"""dsh-borrowed patterns: typed node envelopes, closed status enum, per-run caps."""

import asyncio

import pytest

from src.engine.dag_executor import (
    DAGResult, NodeEnvelope, NodeStatus, Subtask, execute_persisted_dag,
)


class _FakePersistence:
    def __init__(self):
        self.events = []

    async def save_run(self, **kw):
        return "run-1"

    async def save_step_event(self, run_id, step_id, frm, to, error=None):
        self.events.append((step_id, to))

    async def update_run_status(self, run_id, **kw):
        self.status = kw.get("status")


class _Resp:
    def __init__(self, content):
        self.content = content


class _OkAgent:
    async def process(self, text):
        return _Resp("ok-output")


class _BoomAgent:
    async def process(self, text):
        raise RuntimeError("agent exploded")


def test_node_status_is_closed_enum():
    assert {s.value for s in NodeStatus} == {"done", "failed", "skipped", "cancelled"}


def test_node_envelope_ok_property():
    assert NodeEnvelope("n1", NodeStatus.DONE, value="v").ok is True
    assert NodeEnvelope("n1", NodeStatus.FAILED, error="e").ok is False


@pytest.mark.asyncio
async def test_dag_returns_typed_envelopes_for_success_and_failure():
    subs = [
        Subtask(id="a", agent="good", description="do a"),
        Subtask(id="b", agent="bad", description="do b"),
    ]
    res = await execute_persisted_dag(
        subs, {"good": _OkAgent(), "bad": _BoomAgent()}, _FakePersistence(),
    )
    assert isinstance(res, DAGResult)
    assert res.nodes["a"].status is NodeStatus.DONE
    assert res.nodes["a"].value == "ok-output"
    assert res.nodes["b"].status is NodeStatus.FAILED
    assert "exploded" in (res.nodes["b"].error or "")


@pytest.mark.asyncio
async def test_missing_agent_is_a_failed_envelope_not_a_raise():
    subs = [Subtask(id="a", agent="nope", description="x")]
    res = await execute_persisted_dag(subs, {}, _FakePersistence())
    assert res.nodes["a"].status is NodeStatus.FAILED


@pytest.mark.asyncio
async def test_max_total_nodes_backstop_skips_remainder():
    subs = [Subtask(id=f"n{i}", agent="good", description="x") for i in range(5)]
    res = await execute_persisted_dag(
        subs, {"good": _OkAgent()}, _FakePersistence(), max_total_nodes=2,
    )
    done = [n for n in res.nodes.values() if n.status is NodeStatus.DONE]
    skipped = [n for n in res.nodes.values() if n.status is NodeStatus.SKIPPED]
    assert len(done) == 2
    assert len(skipped) == 3


@pytest.mark.asyncio
async def test_semaphore_bounds_concurrency_across_the_whole_run():
    """The cap is per-run, not per-level (the old bug re-created it each level)."""
    live = 0
    peak = 0

    class _Tracking:
        async def process(self, text):
            nonlocal live, peak
            live += 1
            peak = max(peak, live)
            await asyncio.sleep(0.01)
            live -= 1
            return _Resp("x")

    subs = [Subtask(id=f"n{i}", agent="t", description="x") for i in range(6)]
    await execute_persisted_dag(subs, {"t": _Tracking()}, _FakePersistence(), max_parallel=2)
    assert peak <= 2
