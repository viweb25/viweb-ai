import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from vi_api.config.settings import Settings
from vi_api.infrastructure.database.models.base import Base
from vi_api.infrastructure.database.models.organisation import Organisation  # noqa: F401


def configure(connection=None):
    options = {"target_metadata": Base.metadata, "compare_type": True}
    if connection is None:
        options.update(url=Settings().database_url, literal_binds=True)
    else:
        options["connection"] = connection
    context.configure(**options)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = create_async_engine(Settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(configure)
    await engine.dispose()


if context.is_offline_mode():
    configure()
else:
    asyncio.run(online())
