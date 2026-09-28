import uuid

from psycopg.errors import UniqueViolation

from rag.domain.errors import IngestionInProgressError
from rag.domain.models import IngestionReport, IngestionRun
from rag.repository.base_repository import BaseRepository

_COLUMNS = (
    "id, status, archive_name, created_by, started_at, finished_at, "
    "added, updated, unchanged, removed, chunks, error"
)


class IngestionRunRepository(BaseRepository[IngestionRun]):
    row_type = IngestionRun

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
            f"SELECT {_COLUMNS} FROM ingestion_runs ORDER BY started_at DESC LIMIT 1"
        )

    async def running(self) -> IngestionRun | None:
        return await self._fetch_one(
            f"SELECT {_COLUMNS} FROM ingestion_runs WHERE status = 'running'"
        )

    async def finish(self, run_id: uuid.UUID, report: IngestionReport) -> None:
        await self._execute(
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
        await self._execute(
            "UPDATE ingestion_runs "
            "SET status = 'failed', finished_at = now(), error = %s WHERE id = %s",
            (error, run_id),
        )

    async def fail_running(self, error: str) -> int:
        return await self._execute(
            "UPDATE ingestion_runs "
            "SET status = 'failed', finished_at = now(), error = %s "
            "WHERE status = 'running'",
            (error,),
        )
