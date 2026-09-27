"""Used to generate frontend TypeScript types from the backend's Pydantic"""

import json

from pydantic import SecretStr

from rag.app import create_app
from rag.config import (
    AuthConfig,
    CheckpointerConfig,
    OpenAILLM,
    PineconeConfig,
    Settings,
)

_PLACEHOLDER_SETTINGS = Settings(
    _env_file=None,  # pyright: ignore[reportCallIssue] — ignore the real .env, only the schema shape matters here
    LLM=OpenAILLM(API_KEY=SecretStr("placeholder"), MODEL="placeholder"),
    PINECONE=PineconeConfig(
        API_KEY=SecretStr("placeholder"),
        DENSE_INDEX_NAME="placeholder",
        SPARSE_INDEX_NAME="placeholder",
        CLOUD="placeholder",
        REGION="placeholder",
        DENSE_MODEL="placeholder",
        SPARSE_MODEL="placeholder",
        NAMESPACE="placeholder",
    ),
    AUTH=AuthConfig(
        DATABASE_URL=SecretStr("placeholder"), JWT_SECRET=SecretStr("placeholder")
    ),
    CHECKPOINTER=CheckpointerConfig(DATABASE_URL=SecretStr("placeholder")),
)


def main() -> None:
    app = create_app(settings=_PLACEHOLDER_SETTINGS)
    print(json.dumps(app.openapi()))


if __name__ == "__main__":
    main()
