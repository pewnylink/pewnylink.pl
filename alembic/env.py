import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context

# 1. IMPORTY APLIKACJI - pobranie bazy, silnika oraz modeli ORM ze skonsolidowanego pliku db_models
from app.db.session import Base, engine
from app.models.db_models import ReportModel, User, Voucher

# Obiekt konfiguracji Alembica (.ini)
config = context.config

# Konfiguracja logowania
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. POBRANIE PEŁNEGO URL DLA ALEMBICA (BEZ MASKOWANIA HASŁA ***)
config.set_main_option(
    "sqlalchemy.url", 
    engine.url.render_as_string(hide_password=False)
)

# 3. REJESTRACJA METADANYCH MODELI
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Uruchamianie migracji w trybie offline."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Uruchamianie migracji asynchronicznych bezpośrednio z użyciem sprawdzanego engine z app.db.session."""
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """Uruchamianie migracji w trybie online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()