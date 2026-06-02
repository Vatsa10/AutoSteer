from fastapi import APIRouter, Request

router = APIRouter(tags=["agents"])


@router.get("/agents")
async def list_agents(request: Request):
    engine = request.app.state.engine
    if not engine:
        return []
    return engine.list_agents()


@router.get("/departments")
async def list_departments(request: Request):
    engine = request.app.state.engine
    if not engine:
        return []
    return engine.list_departments()
