"""Alembic environment: async engine from the POSTGRES_* variables, only the knowledge base tables.

The Postgres database is shared (a2a_tasks belongs to the A2A layer), so autogenerate looks only at the
tables defined in auxin_knowledge.db.
"""
import asyncio

from alembic import context
from sqlalchemy.engine import Connection

from auxin_knowledge.db import Base, make_engine

target_metadata = Base.metadata
VERSION_TABLE = "knowledge_alembic_version"


def _include_name(name, type_, _parent_names) -> bool:
    return type_ != "table" or name in target_metadata.tables


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=_include_name,
        version_table=VERSION_TABLE,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = make_engine()
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_online())
