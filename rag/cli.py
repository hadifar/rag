import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import uvicorn

from rag.config import get_settings

if TYPE_CHECKING:
    from rag.container import Container

app = typer.Typer(add_completion=False, help="RAG — CLI")


def _run[T](command: Callable[["Container"], Awaitable[T]]) -> T:
    """Runs one command against a container that's opened for it and closed after."""
    from rag.container import build_container

    async def main() -> T:
        async with build_container(get_settings()) as container:
            return await command(container)

    return asyncio.run(main())


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
    from rag.domain.errors import AppError
    from rag.services.ingestion_service.loaders import load_path

    path = _ingest_path(source, latest, get_settings().KNOWLEDGE_BASE_SOURCE)

    try:
        if latest:
            report = _run(
                lambda container: container.ingestion_service.ingest_latest_archive(
                    force=force
                )
            )
        else:
            documents = load_path(path)
            report = _run(
                lambda container: container.ingestion_service.ingest(
                    documents, force=force
                )
            )
    except AppError as exc:
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
    admin: bool = typer.Option(False, help="Allow replacing the knowledge base"),
) -> None:
    """Create a login for a user (there's no public signup endpoint)."""
    from rag.domain.errors import UserAlreadyExistsError

    try:
        user = _run(
            lambda container: container.auth_service.create_user(
                email, password, is_admin=admin
            )
        )
    except UserAlreadyExistsError as exc:
        raise typer.BadParameter(f"a user with email {email!r} already exists") from exc

    role = " (admin)" if user.is_admin else ""
    typer.echo(f"Created user {user.email}{role} ({user.id})")


@app.command(name="set-admin")
def set_admin(
    email: str = typer.Argument(..., help="Email address of an existing user"),
    revoke: bool = typer.Option(False, help="Remove admin rights instead"),
) -> None:
    """Grant (or revoke) admin rights: admins can replace the knowledge base."""
    from rag.domain.errors import UserEmailNotFoundError

    try:
        user = _run(
            lambda container: container.auth_service.set_admin(email, not revoke)
        )
    except UserEmailNotFoundError as exc:
        raise typer.BadParameter(f"no user with email {email!r}") from exc

    typer.echo(f"{user.email} is {'now' if user.is_admin else 'no longer'} an admin")


if __name__ == "__main__":
    app()
