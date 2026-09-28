import asyncio
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from rag.config import get_settings

app = typer.Typer(add_completion=False, help="RAG — CLI")


@app.command()
def serve(
    host: str = typer.Option(None, help="Override HOST from settings"),
    port: int = typer.Option(None, help="Override PORT from settings"),
    reload: bool = typer.Option(False, help="Autoreload (dev only)"),
) -> None:
    """Start the FastAPI app."""
    settings = get_settings()
    uvicorn.run(
        "rag.app:create_app",
        factory=True,
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=reload,
    )


@app.command()
def ingest(
    source: Annotated[
        Path | None,
        typer.Option(
            help="A .zip or directory of .md files; overrides KNOWLEDGE_BASE_SOURCE"
        ),
    ] = None,
    latest: bool = typer.Option(
        False, help="Ingest the most recently uploaded archive (from KB_STORAGE)"
    ),
    force: bool = typer.Option(
        False, help="Re-embed unchanged documents too (after an embedding model change)"
    ),
) -> None:
    """Make the index match the knowledge base: embed new/changed docs, drop removed ones."""
    from rag.container import build_container
    from rag.domain.errors import RagError
    from rag.domain.models import IngestionReport
    from rag.services.ingestion_service.loaders import loader_for_path

    settings = get_settings()
    path = _ingest_path(source, latest, settings.KNOWLEDGE_BASE_SOURCE)

    async def run() -> IngestionReport:
        async with build_container(settings) as container:
            if latest:
                return await container.ingestion_service.ingest_latest_archive(
                    force=force
                )
            loader = loader_for_path(path)
            return await container.ingestion_service.ingest(loader, force=force)

    try:
        report = asyncio.run(run())
    except RagError as exc:
        hint = "--latest" if latest else "--source"
        raise typer.BadParameter(str(exc), param_hint=hint) from exc

    typer.echo(
        f"Ingested {'the latest upload' if latest else path}: "
        f"{report.added} added, {report.updated} updated, "
        f"{report.unchanged} unchanged, {report.removed} removed "
        f"({report.chunks} chunks embedded)"
    )


def _ingest_path(source: Path | None, latest: bool, default: Path) -> Path:
    if latest and source:
        raise typer.BadParameter(
            "use either --latest or --source", param_hint="--latest"
        )
    path = source or default
    if not latest and not path.exists():
        raise typer.BadParameter(f"{path} doesn't exist", param_hint="--source")
    return path


@app.command(name="create-user")
def create_user(
    email: str = typer.Argument(..., help="Email address for the new user"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=True
    ),
) -> None:
    """Create a login for a user (there's no public signup endpoint)."""
    import psycopg

    from rag.container import build_container
    from rag.domain.models import User

    settings = get_settings()

    async def run() -> User:
        async with build_container(settings) as container:
            return await container.auth_service.create_user(email, password)

    try:
        user = asyncio.run(run())
    except psycopg.errors.UniqueViolation as exc:
        raise typer.BadParameter(f"a user with email {email!r} already exists") from exc

    typer.echo(f"Created user {user.email} ({user.id})")


if __name__ == "__main__":
    app()
