import asyncio
from pathlib import Path

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
    source: str = typer.Option(None, help="Override KNOWLEDGE_BASE_DIR from settings"),
) -> None:
    """Load the markdown KB, embed, upsert into the vector store."""
    from rag.container import build_container
    from rag.domain.models import IngestionReport
    from rag.services.ingestion_service.loaders import MarkdownFileLoader

    settings = get_settings()
    loader = MarkdownFileLoader(Path(source) if source else settings.KNOWLEDGE_BASE_DIR)

    async def run() -> IngestionReport:
        async with build_container(settings) as container:
            return await container.ingestion_service.ingest(loader)

    report = asyncio.run(run())
    typer.echo(f"Ingested {report.documents} documents, {report.chunks} chunks")


if __name__ == "__main__":
    app()
