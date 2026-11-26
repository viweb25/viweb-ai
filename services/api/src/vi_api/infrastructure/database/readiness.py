import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# The schema revision (viweb-db Alembic head) this API release is written for.
# Bump it together with each new migration; the API reports "not ready" until it matches.
REQUIRED_SCHEMA_REVISION = "0011"


class DatabaseReadinessRepository:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def is_ready(self) -> bool:
        try:
            async with asyncio.timeout(3):
                async with self.engine.connect() as connection:
                    revision = await connection.scalar(
                        text("SELECT version_num FROM alembic_version")
                    )
                    return revision == REQUIRED_SCHEMA_REVISION
        except Exception:
            return False
