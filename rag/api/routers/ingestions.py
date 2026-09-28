import uuid

from fastapi import APIRouter, BackgroundTasks, UploadFile

from rag.api.deps import AdminUserDep, IngestionServiceDep
from rag.api.schema.ingestions import IngestionRunResponse

# Admin-only: app.py includes this router behind get_current_admin.
router = APIRouter(prefix="/api/ingestions", tags=["ingestions"])


@router.post("", status_code=202)
async def upload_knowledge_base(
    file: UploadFile,
    admin: AdminUserDep,
    ingestion_service: IngestionServiceDep,
    background_tasks: BackgroundTasks,
) -> IngestionRunResponse:
    """Replaces the knowledge base with the uploaded .zip of .md files. Returns right
    away with a `running` run; poll `GET /api/ingestions/{id}` until it ends.
    """
    run = await ingestion_service.start_upload(await file.read(), admin.id)
    background_tasks.add_task(ingestion_service.complete_run, run)
    return IngestionRunResponse.from_domain(run)


# Declared before /{run_id}, so "latest" isn't parsed as a run id.
@router.get("/latest")
async def get_latest_run(
    ingestion_service: IngestionServiceDep,
) -> IngestionRunResponse | None:
    run = await ingestion_service.latest_run()
    return IngestionRunResponse.from_domain(run) if run else None


@router.get("/{run_id}")
async def get_run(
    run_id: uuid.UUID, ingestion_service: IngestionServiceDep
) -> IngestionRunResponse:
    return IngestionRunResponse.from_domain(await ingestion_service.get_run(run_id))
