import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


from src.config import get_settings

API_KEY = get_settings().autosteer_api_key or "dev-secret-change-me-in-production"

@pytest.fixture
def app():
    application = create_app()
    application.state.engine = None
    return application

@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY}


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
async def test_list_agents(app, auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/agents", headers=auth_headers)
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)


@pytest.mark.asyncio
async def test_list_departments(app, auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/departments", headers=auth_headers)
    assert response.status_code == 200
    departments = response.json()
    assert isinstance(departments, list)
