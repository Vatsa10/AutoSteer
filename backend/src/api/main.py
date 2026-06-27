import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agents, approvals, billing, chat, conversations, custom_agents, files, integrations, memory, preferences, prompts, tools, websocket, workflows
from src.auth import setup_auth
from src.config import get_settings
from src.database import get_engine, init_db
from src.engine.llm import LLMProvider
from src.engine.memory_manager import MemoryManager
from src.engine.orchestrator import OrchestrationEngine
from src.engine.tool_executor import get_tool_registry
from src.messaging.bus import MessageBus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB, MessageBus, LLM, and Engine
    settings = get_settings()

    # 1. Initialize database (create tables)
    try:
        await init_db()
        app.state.db_initialized = True
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        app.state.db_initialized = False

    # 2. Initialize MessageBus (Redis)
    message_bus = MessageBus(redis_url=settings.redis_url)
    app.state.message_bus = message_bus
    message_bus_task = asyncio.create_task(message_bus.start_listening())
    app.state.message_bus_task = message_bus_task

    # 3. Initialize LLM Provider
    llm = LLMProvider(
        default_model=settings.default_llm_model,
        anthropic_api_key=settings.anthropic_api_key,
        openai_api_key=settings.openai_api_key,
    )

    # 4. Initialize Orchestration Engine
    try:
        engine = OrchestrationEngine(
            definitions_dir="src/agents/definitions",
            llm=llm,
            message_bus=message_bus,
        )
    except Exception as e:
        print(f"Warning: Engine initialization failed: {e}")
        engine = None
    app.state.engine = engine

    # 5. Initialize tool registry
    tool_registry = get_tool_registry()
    app.state.tool_registry = tool_registry

    # Initialize memory manager
    app.state.memory_manager = MemoryManager(conversation_id="global")

    yield

    # Shutdown
    if hasattr(app.state, "message_bus_task") and app.state.message_bus_task:
        app.state.message_bus_task.cancel()
        try:
            await app.state.message_bus_task
        except asyncio.CancelledError:
            pass
    await message_bus.close()
    sql_engine = get_engine()
    await sql_engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoSteer",
        version="0.1.0",
        description="Multi-agent orchestration — 42 AI agents across 12 departments",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://tryAutoSteer.online"],
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-API-Key"],
    )

    app.include_router(chat.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(tools.router, prefix="/api")
    app.include_router(integrations.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(prompts.router, prefix="/api")
    app.include_router(custom_agents.router, prefix="/api")
    app.include_router(billing.router, prefix="/api")
    app.include_router(preferences.router, prefix="/api")
    app.include_router(memory.router, prefix="/api")
    app.include_router(workflows.router, prefix="/api")
    app.include_router(approvals.router, prefix="/api")
    app.include_router(websocket.router)

    # Setup auth (no-op if AutoSteer_API_KEY is not set)
    auth_enabled = setup_auth(app)
    app.state.auth_enabled = auth_enabled

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
