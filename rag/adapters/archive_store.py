import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import ContainerClient

from rag.config import AzureBlobKbStorage, LocalKbStorage, Settings
from rag.domain.ports import ArchiveStorePort


class LocalArchiveStore:
    """ArchiveStorePort on local disk (uv, and a volume under docker compose)."""

    def __init__(self, directory: Path):
        self._directory = directory

    async def asave(self, data: bytes) -> str:
        return await asyncio.to_thread(self._save, data)

    async def aread(self, name: str) -> bytes:
        return await asyncio.to_thread((self._directory / name).read_bytes)

    async def alatest(self) -> str | None:
        return await asyncio.to_thread(self._latest)

    def _save(self, data: bytes) -> str:
        self._directory.mkdir(parents=True, exist_ok=True)
        name = _new_name()
        # Write, then rename (atomic): a half-written file never becomes the latest.
        partial = self._directory / f".{name}.partial"
        partial.write_bytes(data)
        partial.rename(self._directory / name)
        return name

    def _latest(self) -> str | None:
        return max((path.name for path in self._directory.glob("*.zip")), default=None)


class AzureBlobArchiveStore:
    """ArchiveStorePort on an Azure Blob Storage container."""

    def __init__(self, container: ContainerClient):
        self._container = container

    async def asave(self, data: bytes) -> str:
        name = _new_name()
        await self._container.upload_blob(name, data, overwrite=False)
        return name

    async def aread(self, name: str) -> bytes:
        download = await self._container.download_blob(name)
        return await download.readall()

    async def alatest(self) -> str | None:
        latest = None
        async for name in self._container.list_blob_names():
            if name.endswith(".zip") and (latest is None or name > latest):
                latest = name
        return latest


@asynccontextmanager
async def open_archive_store(settings: Settings) -> AsyncGenerator[ArchiveStorePort]:
    match settings.KB_STORAGE:
        case LocalKbStorage() as config:
            yield LocalArchiveStore(config.DIR)
        case AzureBlobKbStorage() as config:
            async with (
                DefaultAzureCredential() as credential,
                ContainerClient(
                    config.ACCOUNT_URL, config.CONTAINER, credential=credential
                ) as container,
            ):
                yield AzureBlobArchiveStore(container)


def _new_name() -> str:
    """UTC timestamp first, so names sort by upload time; the suffix keeps two uploads
    in the same microsecond apart.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}.zip"
