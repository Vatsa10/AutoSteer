from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agents, chat, conversations, websocket
from src.engine.llm import LLMProvider
from src.engine.orchestrator import OrchestrationEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize engine
    llm = LLMProvider()
    try:
        engine = OrchestrationEngine(
            definitions_dir="src/agents/definitions",
            llm=llm,
        )
    except Exception as e:
        print(f"Warning: Engine initialization failed: {e}")
        engine = None
    app.state.engine = engine
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoSteer",
        version="0.1.0",
        description="Multi-agent orchestration — 42 AI agents across 12 departments",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(websocket.router)

    @app.get("/api/health")
    async def health():
        engine = app.state.engine
        agent_count = len(engine.list_agents()) if engine else 0
        dept_count = len(engine.list_departments()) if engine else 0
        return {
            "status": "ok",
            "version": "0.1.0",
            "agents_loaded": agent_count,
            "departments_loaded": dept_count,
        }

    @app.get("/api/status")
    async def status(request: Request):
        engine = request.app.state.engine
        if not engine:
            return {
                "total_agents": 0,
                "total_departments": 0,
                "llm_provider": "not initialized",
                "uptime_seconds": 0,
            }
        return {
            "total_agents": len(engine.list_agents()),
            "total_departments": len(engine.list_departments()),
            "llm_provider": getattr(engine.llm, "provider", "configured"),
            "uptime_seconds": 0,
        }

    return app


app = create_app()
