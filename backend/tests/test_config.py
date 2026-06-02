from src.config import Settings


def test_settings_defaults():
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.app_name == "AutoSteer"
    assert settings.debug is False
    assert settings.default_llm_provider == "openai"
    assert settings.default_llm_model == "gpt-4o"


def test_settings_llm_overrides():
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
        default_llm_provider="openai",
        default_llm_model="gpt-4o",
    )
    assert settings.default_llm_provider == "openai"
    assert settings.default_llm_model == "gpt-4o"
