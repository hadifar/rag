from collections.abc import Mapping
from typing import Any

import jwt

from rag.domain.errors import InvalidTokenError


class JwtTokenCodec:
    def __init__(self, secret: str, algorithm: str):
        self._secret = secret
        self._algorithm = algorithm

    def encode(self, claims: Mapping[str, Any]) -> str:
        return jwt.encode(dict(claims), self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTokenError("expired") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError("malformed") from exc
