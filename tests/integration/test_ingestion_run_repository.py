"""Runs the ingestion-run SQL against real Postgres (migrated with `alembic upgrade head`).
Every run here has an `it-` archive name, and is deleted afterwards.
"""

from collections.abc import AsyncGenerator
from datetime import timedelta

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


async def test_an_ended_run_keeps_its_outcome(runs: IngestionRunRepository) -> None:
    run = await runs.create("it-ended.zip", None)
    await runs.fail(run.id, "stale")

    await runs.finish(
        run.id, IngestionReport(added=1, updated=0, unchanged=0, removed=0, chunks=1)
    )
    await runs.fail(run.id, "later")

    done = await runs.get(run.id)
    assert done is not None
    assert (done.status, done.error, done.added) == ("failed", "stale", None)


async def test_only_a_run_whose_lease_lapsed_is_failed(
    runs: IngestionRunRepository, db_pool: AsyncConnectionPool[AsyncConnection]
) -> None:
    run = await runs.create("it-lease.zip", None)

    assert await runs.fail_stale("stale", timedelta(minutes=1)) == 0

    async with db_pool.connection() as conn:
        await conn.execute(
            "UPDATE ingestion_runs SET heartbeat_at = now() - interval '2 minutes' "
            "WHERE id = %s",
            (run.id,),
        )
    await runs.heartbeat(run.id)  # renewed: alive again
    assert await runs.fail_stale("stale", timedelta(minutes=1)) == 0

    async with db_pool.connection() as conn:
        await conn.execute(
            "UPDATE ingestion_runs SET heartbeat_at = now() - interval '2 minutes' "
            "WHERE id = %s",
            (run.id,),
        )
    assert await runs.fail_stale("stale", timedelta(minutes=1)) == 1
    failed = await runs.get(run.id)
    assert failed is not None
    assert (failed.status, failed.error) == ("failed", "stale")
