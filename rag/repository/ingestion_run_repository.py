import uuid
from typing import LiteralString

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from rag.domain.errors import IngestionInProgressError
from rag.domain.models import IngestionReport, IngestionRun

_COLUMNS = (
    "id, status, archive_name, created_by, started_at, finished_at, "
    "added, updated, unchanged, removed, chunks, error"
)


class IngestionRunRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]):
        self._pool = pool

    async def create(
        self, archive_name: str, created_by: uuid.UUID | None
    ) -> IngestionRun:
        try:
            run = await self._fetch_one(
                "INSERT INTO ingestion_runs (status, archive_name, created_by) "
                f"VALUES ('running', %s, %s) RETURNING {_COLUMNS}",
                (archive_name, created_by),
            )
        except UniqueViolation as exc:  # ux_ingestion_runs_one_running
            raise IngestionInProgressError() from exc
        assert run is not None  # INSERT ... RETURNING always yields a row
        return run

    async def get(self, run_id: uuid.UUID) -> IngestionRun | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM ingestion_runs WHERE id = %s", (run_id,)
        )

    async def latest(self) -> IngestionRun | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM ingestion_runs ORDER BY started_at DESC LIMIT 1",
            (),
        )

    async def running(self) -> IngestionRun | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM ingestion_runs WHERE status = 'running'", ()
        )

    async def finish(self, run_id: uuid.UUID, report: IngestionReport) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                UPDATE ingestion_runs
                SET status = 'succeeded', finished_at = now(), added = %s,
                    updated = %s, unchanged = %s, removed = %s, chunks = %s
                WHERE id = %s
                """,
                (
                    report.added,
                    report.updated,
                    report.unchanged,
                    report.removed,
                    report.chunks,
                    run_id,
                ),
            )

    async def fail(self, run_id: uuid.UUID, error: str) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE ingestion_runs "
                "SET status = 'failed', finished_at = now(), error = %s WHERE id = %s",
                (error, run_id),
            )

    async def fail_running(self, error: str) -> int:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE ingestion_runs "
                "SET status = 'failed', finished_at = now(), error = %s "
                "WHERE status = 'running'",
                (error,),
            )
            return cur.rowcount

    async def _fetch_one(
        self, query: LiteralString, params: tuple
    ) -> IngestionRun | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=class_row(IngestionRun)) as cur,
        ):
            await cur.execute(query, params)
            return await cur.fetchone()
