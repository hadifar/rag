from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class LocalKbStorageConfig(BaseModel):
    BACKEND: Literal["local"] = "local"
    DIR: Path = Path("data/uploads")


class AzureBlobKbStorageConfig(BaseModel):
    """Authenticates with DefaultAzureCredential: the Web App's managed identity in
    Azure, `az login` locally — no keys.
    """

    BACKEND: Literal["azure_blob"] = "azure_blob"
    ACCOUNT_URL: str  # https://<account>.blob.core.windows.net
    CONTAINER: str = "kb-archives"


KbStorageConfig = Annotated[
    LocalKbStorageConfig | AzureBlobKbStorageConfig, Field(discriminator="BACKEND")
]
