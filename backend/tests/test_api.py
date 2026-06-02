import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.fixture
def app():
    application = create_app()
    # Set engine to None so endpoints work without lifespan running
    application.state.engine = None
    return application


@pytest.mark.asyncio
async def test_health_check(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_agents(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)


@pytest.mark.asyncio
async def test_list_departments(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/departments")
    assert response.status_code == 200
    departments = response.json()
    assert isinstance(departments, list)
