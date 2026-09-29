"""Runs the ingestion-run SQL against real Postgres (migrated with `alembic upgrade head`).
Every run here has an `it-` archive name, and is deleted afterwards.
"""

from collections.abc import AsyncGenerator

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag.domain.errors import IngestionInProgressError
from rag.domain.models import IngestionReport
from rag.repository.ingestion_run_repository import IngestionRunRepository


@pytest.fixture
async def runs(
    db_pool: AsyncConnectionPool[AsyncConnection],
) -> AsyncGenerator[IngestionRunRepository]:
    yield IngestionRunRepository(db_pool)
    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM ingestion_runs WHERE archive_name LIKE 'it-%'")


async def test_only_one_run_can_be_running(runs: IngestionRunRepository) -> None:
    first = await runs.create("it-first.zip", None)

    with pytest.raises(IngestionInProgressError):
        await runs.create("it-second.zip", None)

    await runs.fail(first.id, "boom")
    second = await runs.create("it-second.zip", None)
    assert (await runs.running()) == second
    await runs.fail(second.id, "cleanup")


async def test_finish_records_the_report(runs: IngestionRunRepository) -> None:
    run = await runs.create("it-finish.zip", None)

    await runs.finish(
        run.id, IngestionReport(added=3, updated=1, unchanged=5, removed=2, chunks=4)
    )

    done = await runs.get(run.id)
    assert done is not None
    assert (done.status, done.added, done.removed, done.chunks) == (
        "succeeded",
        3,
        2,
        4,
    )
    assert done.finished_at is not None
    assert (await runs.latest()) == done
    assert await runs.running() is None
