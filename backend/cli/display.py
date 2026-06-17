from rich.console import Console
from rich.table import Table

console = Console()


def show_workflow_table(workflows: list[dict]) -> None:
    table = Table(title="Workflows")
    table.add_column("Name")
    table.add_column("Steps")
    table.add_column("Description")
    for w in workflows:
        table.add_row(
            w.get("name", "?"),
            str(w.get("step_count", "?")),
            w.get("description", ""),
        )
    console.print(table)


def show_agent_table() -> None:
    import httpx
    import os
    api = os.getenv("RAAH_API_URL", "http://localhost:8000")
    try:
        r = httpx.get(f"{api}/api/agents", timeout=5)
        agents = r.json()
        table = Table(title="Agents")
        table.add_column("Role")
        table.add_column("Name")
        table.add_column("Department")
        table.add_column("Tasks")
        for a in agents:
            table.add_row(
                a.get("role", "?"),
                a.get("name", "?"),
                a.get("department", "?"),
                ", ".join(a.get("tasks", [])),
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]Cannot reach backend: {e}[/red]")
