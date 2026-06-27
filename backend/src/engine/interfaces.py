"""
Protocol interfaces for AutoSteer's orchestration layer.

Inspired by Kokoro-AI-Workflow-Engine's Protocol-based contracts.
Uses PEP 544 structural subtyping — any object with the right methods
satisfies the contract without inheritance. Tests inject fakes trivially.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StepProtocol(Protocol):
    """A single unit of work in a workflow pipeline."""

    async def run(self, state: dict[str, Any], config: dict[str, Any]) -> Any:
        """Execute this step, reading/writing the shared state dict."""
        ...


@runtime_checkable
class AgentProtocol(Protocol):
    """An agent that can process a message and return a result."""

    async def process(self, message: str) -> Any: ...

    async def process_stream(self, message: str) -> Any: ...

    @property
    def role(self) -> str: ...


@runtime_checkable
class ToolProtocol(Protocol):
    """A callable tool that agents can invoke."""

    async def __call__(self, **kwargs: Any) -> str: ...


class WorkflowRepository(Protocol):
    """Persistence contract for workflow runs and step events."""

    async def save_run(
        self,
        workflow_name: str,
        status: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> str: ...

    async def save_step_event(
        self,
        run_id: str,
        step_id: str,
        from_status: str,
        to_status: str,
        error: str | None = None,
    ) -> None: ...

    async def get_run(self, run_id: str) -> dict[str, Any] | None: ...

    async def list_runs(
        self, workflow_name: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]: ...
