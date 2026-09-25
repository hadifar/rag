"""Used to generate frontend TypeScript types from the backend's Pydantic"""

import json

from pydantic import SecretStr

from rag.app import create_app
from rag.config import OpenAILLM, Settings

_PLACEHOLDER_SETTINGS = Settings(
    _env_file=None,  # pyright: ignore[reportCallIssue] — ignore the real .env, only the schema shape matters here
    LLM=OpenAILLM(API_KEY=SecretStr("placeholder"), MODEL="placeholder"),
    PINECONE_API_KEY=SecretStr("placeholder"),
    PINECONE_DENSE_INDEX_NAME="placeholder",
    PINECONE_SPARSE_INDEX_NAME="placeholder",
    PINECONE_CLOUD="placeholder",
    PINECONE_REGION="placeholder",
    PINECONE_DENSE_MODEL="placeholder",
    PINECONE_SPARSE_MODEL="placeholder",
    PINECONE_NAMESPACE="placeholder",
)


def main() -> None:
    app = create_app(settings=_PLACEHOLDER_SETTINGS)
    print(json.dumps(app.openapi()))


if __name__ == "__main__":
    main()
