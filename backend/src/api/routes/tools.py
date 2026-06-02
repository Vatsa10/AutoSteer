from fastapi import APIRouter, Request

from src.engine.tool_executor import ToolRegistry, execute_tool

router = APIRouter()


@router.get("/tools")
async def list_tools(request: Request):
    """List all available tools and their schemas."""
    registry: ToolRegistry | None = getattr(request.app.state, "tool_registry", None)
    if not registry:
        return {"tools": [], "count": 0}

    tools = []
    for name in sorted(registry.list_tools()):
        schema = registry.get_schema(name)
        tools.append({
            "name": name,
            "description": schema.get("description", "") if schema else "",
            "parameters": schema.get("parameters", {}) if schema else {},
        })

    return {"tools": tools, "count": len(tools)}


@router.post("/tools/{tool_name}/execute")
async def execute_tool_endpoint(tool_name: str, body: dict, request: Request):
    """Execute a specific tool with given arguments."""
    registry: ToolRegistry | None = getattr(request.app.state, "tool_registry", None)
    if not registry:
        return {"success": False, "error": "Tool registry not initialized"}

    arguments = body.get("arguments", {})
    result = await execute_tool(registry, tool_name, arguments)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
    }
