"""The 'dream' cycle — background memory consolidation.

Inspired by GoogleCloudPlatform's always-on-memory-agent, adapted to AutoSteer's
Neon/Postgres + LiteLLM stack (no Google ADK, no SQLite). Periodically the system
reads raw facts accumulated since the last run and distills them into durable,
connected insights (the knowledge catalog). Cheap model, runs off a cron ping.
"""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.memory_fact import MemoryFact
from src.models.memory_insight import MemoryInsight
from src.models.shared_state import SharedState

_WATERMARK_KEY = "memory:dream_watermark"  # ISO timestamp of last consolidated fact

_SYSTEM = (
    "You are a memory consolidation engine. You merge raw facts into durable, "
    "de-duplicated insights and surface connections between them. Return JSON only."
)


async def consolidate(session: AsyncSession, llm, max_facts: int = 60) -> dict:
    """Run one consolidation pass. Returns a summary dict.

    Reads facts created after the stored watermark, asks the LLM to distill them
    into insights, persists new MemoryInsight rows, and advances the watermark.
    Safe to call repeatedly (idempotent-ish via the watermark).
    """
    watermark = await _get_watermark(session)
    q = select(MemoryFact)
    if watermark:
        q = q.where(MemoryFact.created_at > watermark)
    q = q.order_by(MemoryFact.created_at.asc()).limit(max_facts)
    facts = (await session.execute(q)).scalars().all()

    if not facts:
        return {"consolidated": 0, "insights_created": 0, "reason": "no new facts"}

    existing_titles = await _recent_insight_titles(session)
    payload = "\n".join(
        f"- [{f.fact_type}] {f.key}: {f.value} (conv={f.conversation_id})" for f in facts
    )
    prompt = f"""Consolidate these raw memory facts into durable insights.

Merge duplicates, connect related facts, and rate importance 1-5.
Avoid repeating these existing insights: {existing_titles or 'none'}.

Facts:
{payload}

Return JSON: {{"insights": [{{"title": "...", "body": "...", "topics": ["..."],
"connections": ["related topic or title"], "importance": 1-5}}]}}
Only include genuinely useful, non-trivial insights (max 8)."""

    from src.engine.llm import LLMMessage

    resp = await llm.complete(
        messages=[LLMMessage(role="user", content=prompt)],
        system_prompt=_SYSTEM,
        temperature=0.2,
        max_tokens=1200,
        json_mode=True,
    )
    insights = _parse_insights(resp)

    conv_ids = sorted({f.conversation_id for f in facts})
    created = 0
    for ins in insights[:8]:
        title = str(ins.get("title", "")).strip()
        body = str(ins.get("body", "")).strip()
        if not title or not body:
            continue
        session.add(
            MemoryInsight(
                id=uuid.uuid4().hex[:16],
                title=title[:255],
                body=body,
                topics=_as_list(ins.get("topics")),
                connections=_as_list(ins.get("connections")),
                importance=_clamp_importance(ins.get("importance")),
                source_conversations=conv_ids,
            )
        )
        created += 1

    # Advance watermark to the newest fact we processed.
    await _set_watermark(session, facts[-1].created_at)
    await session.commit()
    return {"consolidated": len(facts), "insights_created": created}


def _parse_insights(resp) -> list[dict]:
    data = getattr(resp, "structured", None)
    if not isinstance(data, dict):
        try:
            data = json.loads(resp.content)
        except (json.JSONDecodeError, TypeError):
            return []
    insights = data.get("insights", data if isinstance(data, list) else [])
    return insights if isinstance(insights, list) else []


def _as_list(v) -> list:
    if isinstance(v, list):
        return [str(x) for x in v]
    if v:
        return [str(v)]
    return []


def _clamp_importance(v) -> int:
    try:
        return max(1, min(5, int(v)))
    except (TypeError, ValueError):
        return 3


async def _recent_insight_titles(session: AsyncSession, limit: int = 30) -> str:
    r = await session.execute(
        select(MemoryInsight.title).order_by(MemoryInsight.created_at.desc()).limit(limit)
    )
    return ", ".join(t for (t,) in r.all())


async def _get_watermark(session: AsyncSession) -> datetime | None:
    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == "default", SharedState.key == _WATERMARK_KEY
        )
    )
    row = r.scalar_one_or_none()
    if row and row.value and row.value.get("ts"):
        try:
            return datetime.fromisoformat(row.value["ts"])
        except ValueError:
            return None
    return None


async def _set_watermark(session: AsyncSession, ts: datetime) -> None:
    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == "default", SharedState.key == _WATERMARK_KEY
        )
    )
    row = r.scalar_one_or_none()
    val = {"ts": ts.isoformat()}
    if row:
        row.value = val
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(row, "value")
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(
            SharedState(
                workspace_id="default",
                key=_WATERMARK_KEY,
                value=val,
                owner="system",
                updated_at=datetime.now(timezone.utc),
            )
        )
