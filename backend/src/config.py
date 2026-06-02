from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AutoSteer"
    debug: bool = False

    # Database
    database_url: str
    redis_url: str

    # LLM
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Agent config
    agents_dir: str = "src/agents/definitions"
    max_concurrent_departments: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
