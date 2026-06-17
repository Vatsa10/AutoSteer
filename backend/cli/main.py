import typer
from pathlib import Path
from rich.console import Console
from cli.display import show_workflow_table, show_agent_table

app = typer.Typer(help="Raah — multi-agent orchestration CLI")
console = Console()


@app.command()
def validate(workflow: Path):
    """Validate a workflow YAML without executing it."""
    import yaml
    from src.api.routes.workflows import WorkflowDefinition
    try:
        raw = yaml.safe_load(workflow.read_text())
        wf = WorkflowDefinition(**raw)
        console.print(f"[green]valid[/green] {wf.name} ({len(wf.steps)} steps)")
    except Exception as e:
        console.print(f"[red]invalid[/red] {e}")
        raise typer.Exit(1)


@app.command()
def status():
    """Show agent and tool inventory."""
    show_agent_table()
