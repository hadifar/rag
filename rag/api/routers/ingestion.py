import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile

from rag.api.deps import AdminUserDep, IngestionServiceDep, get_current_admin
from rag.api.schema.ingestion import IngestionRunResponse

router = APIRouter(
    prefix="/api/ingestions",
    tags=["ingestions"],
    dependencies=[Depends(get_current_admin)],
)


async def _read_archive(
    file: UploadFile, ingestion_service: IngestionServiceDep
) -> bytes:
    """One byte over the limit is enough for the service to reject the upload, without
    ever holding an oversized one in memory.
    """
    return await file.read(ingestion_service.max_archive_bytes + 1)


@router.post("", status_code=202)
async def upload_knowledge_base(
    archive: Annotated[bytes, Depends(_read_archive)],
    admin: AdminUserDep,
    ingestion_service: IngestionServiceDep,
    background_tasks: BackgroundTasks,
) -> IngestionRunResponse:
    """Replaces the knowledge base with the uploaded .zip of .md files. Returns right
    away with a `running` run; poll `GET /api/ingestions/{id}` until it ends.
    """
    run = await ingestion_service.start_upload(archive, admin.id)
    background_tasks.add_task(ingestion_service.complete_run, run)
    return IngestionRunResponse.model_validate(run)


# Declared before /{run_id}, so "latest" isn't parsed as a run id.
@router.get("/latest")
async def get_latest_run(
    ingestion_service: IngestionServiceDep,
) -> IngestionRunResponse | None:
    run = await ingestion_service.latest_run()
    return IngestionRunResponse.model_validate(run) if run else None


@router.get("/{run_id}")
async def get_run(
    run_id: uuid.UUID, ingestion_service: IngestionServiceDep
) -> IngestionRunResponse:
    return IngestionRunResponse.model_validate(await ingestion_service.get_run(run_id))
