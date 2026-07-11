from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.models.base import Base
# Import all models so metadata is populated
import src.models  # noqa: F401
from src.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
# Use sync URL for alembic (psycopg2 instead of asyncpg)
db_url = settings.db_url or config.get_main_option("sqlalchemy.url", "")
if "asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "+psycopg2").replace("asyncpg", "psycopg2")
# If still async (from Neon URL), force psycopg2
if "+psycopg2" not in db_url and "postgresql" in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
    if "postgresql+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "+psycopg2")

config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
