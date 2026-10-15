"""The shared A2A task store: one Postgres table (`a2a_tasks`) for every agent.

Each row's `owner` is the agent that executed the task, so one table shows the whole flow.
"""
import asyncio
import logging
import os
import warnings

from a2a.server.tasks import DatabaseTaskStore
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

log = logging.getLogger("auxin.a2a")

TABLE = "a2a_tasks"


def database_url() -> str:
    """postgresql+asyncpg://… from AUXIN_DATABASE_URL, or built from the POSTGRES_* variables."""
    url = os.environ.get("AUXIN_DATABASE_URL")
    if url:
        return url
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]
    host = os.environ.get("POSTGRES_HOST", "postgres")
    return f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"


# a2a-sdk builds the model for a custom table name with the same class name; harmless.
warnings.filterwarnings("ignore", message=".*same class name and module name as a2a.server.models.TaskModel")


async def open_task_store(agent: str, attempts: int = 30) -> DatabaseTaskStore:
    """Connect and create the table if needed; waits for Postgres to come up."""
    store = DatabaseTaskStore(
        create_async_engine(database_url(), pool_pre_ping=True),
        table_name=TABLE,
        owner_resolver=lambda _context: agent,
    )
    for attempt in range(1, attempts + 1):
        try:
            await store.initialize()
            return store
        except (OSError, DBAPIError) as exc:
            # Postgres still starting, or another agent creating the table at the same moment.
            if attempt == attempts:
                raise
            log.info("task store not ready (%s), retrying", type(exc).__name__)
            await asyncio.sleep(2)
    raise AssertionError("unreachable")
