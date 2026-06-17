from src.config import Settings


def test_settings_defaults():
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.app_name == "Raah"
    assert settings.debug is False
    assert settings.default_llm_provider == "openai"
    assert settings.default_llm_model == "gpt-4o-mini"


def test_settings_llm_overrides():
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
        default_llm_provider="anthropic",
        default_llm_model="claude-sonnet-4-6",
    )
    assert settings.default_llm_provider == "anthropic"
    assert settings.default_llm_model == "claude-sonnet-4-6"
