from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from rag.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Only picks SQLAlchemy's psycopg3 dialect: the connection itself comes from the app's
# DATABASE settings, passed straight to psycopg, so no credentials go through a URL.
_DIALECT_URL = "postgresql+psycopg://"


def run_migrations_offline() -> None:
    context.configure(
        url=_DIALECT_URL,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _DIALECT_URL
    connectable = engine_from_config(
        configuration,
        poolclass=pool.NullPool,
        connect_args=get_settings().DATABASE.connect_kwargs(),
    )

    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
