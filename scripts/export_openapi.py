"""Dump the API's OpenAPI schema to stdout.

Used to generate frontend TypeScript types from the backend's Pydantic
models (see scripts/generate_frontend_types.sh), so the two stay in sync.
Builds the app with placeholder settings — real credentials aren't needed
to produce the schema.
"""

import json

from pydantic import SecretStr

from rag.app import create_app
from rag.config import Settings

_PLACEHOLDER_SETTINGS = Settings(
    _env_file=None,  # pyright: ignore[reportCallIssue] — ignore the real .env, only the schema shape matters here
    OPENAI_API_KEY=SecretStr("placeholder"),
    OPENAI_MODEL="placeholder",
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
