from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["agents"])


@router.get("/agents")
async def list_agents(request: Request):
    engine = request.app.state.engine
    if not engine:
        return []
    return engine.list_agents()


@router.get("/agents/{role}")
async def get_agent(role: str, request: Request):
    engine = request.app.state.engine
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    for agent in engine.list_agents():
        if agent["role"] == role:
            return agent
    raise HTTPException(status_code=404, detail=f"Agent '{role}' not found")


@router.get("/departments")
async def list_departments(request: Request):
    engine = request.app.state.engine
    if not engine:
        return []
    return engine.list_departments()
