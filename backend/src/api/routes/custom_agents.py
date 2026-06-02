"""Custom agent creation API (DB-backed)."""

import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from src.models.agent import Agent

router = APIRouter(tags=["custom-agents"])


class CustomAgentCreate(BaseModel):
    name: str
    role: str
    department: str
    identity: str
    tools: list[str] = []
    tasks: dict = {}


@router.get("/custom-agents")
async def list_custom_agents(request: Request):
    from src.database import get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Agent).where(Agent.agent_type == "custom"))
        agents = result.scalars().all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "department": a.department,
                "tools": a.agent_config.get("tools", []),
                "is_active": a.is_active,
            }
            for a in agents
        ]


@router.post("/custom-agents")
async def create_custom_agent(body: CustomAgentCreate, request: Request):
    from src.database import get_session_factory
    agent_id = str(uuid.uuid4())
    role = body.role.lower().replace(" ", "_")

    soul_config = {
        "name": body.name,
        "identity": body.identity,
        "personality": {"tone": "professional", "communication_style": "concise", "values": []},
        "expertise_areas": [body.department],
        "decision_boundaries": {"can_decide": [], "must_escalate": []},
    }
    agent_config = {
        "name": body.name,
        "role": role,
        "tools": body.tools,
        "tasks": body.tasks or {"default": {"description": "General tasks", "inputs": [], "outputs": [], "sla": "1 hour"}},
        "workflows": {},
    }

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(select(Agent).where(Agent.role == role))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Agent role '{role}' already exists")

        agent = Agent(
            id=agent_id,
            name=body.name,
            role=role,
            department=body.department,
            agent_type="custom",
            soul_config=soul_config,
            agent_config=agent_config,
            is_active=True,
        )
        session.add(agent)
        await session.commit()

    return {"ok": True, "id": agent_id, "role": role, "note": "Restart engine or hot-reload to activate in routing."}


@router.delete("/custom-agents/{role}")
async def delete_custom_agent(role: str, request: Request):
    from src.database import get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Agent).where(Agent.role == role, Agent.agent_type == "custom"))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Custom agent not found")
        await session.delete(agent)
        await session.commit()
    return {"ok": True}
