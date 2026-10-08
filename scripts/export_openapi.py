"""Used to generate frontend TypeScript types from the backend's Pydantic"""

import json

from pydantic import SecretStr

from rag.app import create_app
from rag.config import (
    AuthConfig,
    OpenAILLMConfig,
    Settings,
)

_PLACEHOLDER_SETTINGS = Settings(
    _env_file=None,  # pyright: ignore[reportCallIssue] — ignore the real .env, only the schema shape matters here
    LLM=OpenAILLMConfig(API_KEY=SecretStr("placeholder")),
    DATABASE_URL=SecretStr("placeholder"),
    AUTH=AuthConfig(JWT_SECRET=SecretStr("placeholder")),
)


def main() -> None:
    app = create_app(settings=_PLACEHOLDER_SETTINGS)
    print(json.dumps(app.openapi()))


if __name__ == "__main__":
    main()
