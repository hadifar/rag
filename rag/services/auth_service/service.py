import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from rag.domain.errors import (
    AdminRequiredError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserEmailNotFoundError,
    UserNotFoundError,
)
from rag.domain.models import User
from rag.domain.ports import UserRepositoryPort


class _TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class AuthService:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        jwt_secret: str,
        jwt_algorithm: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ):
        self._user_repository = user_repository
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._hasher = PasswordHasher()

    async def create_user(
        self, email: str, password: str, *, is_admin: bool = False
    ) -> User:
        return await self._user_repository.create(
            email, self._hasher.hash(password), is_admin=is_admin
        )

    async def set_admin(self, email: str, is_admin: bool) -> User:
        user = await self._user_repository.set_admin(email, is_admin)
        if user is None:
            raise UserEmailNotFoundError(email)
        return user

    @staticmethod
    def require_admin(user: User) -> User:
        if not user.is_admin:
            raise AdminRequiredError()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._user_repository.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError()
        try:
            self._hasher.verify(user.hashed_password, password)
        except VerifyMismatchError as exc:
            raise InvalidCredentialsError() from exc
        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    def create_access_token(self, user: User) -> str:
        return self._encode(user.id, _TokenType.ACCESS, self._access_ttl)

    def create_refresh_token(self, user: User) -> str:
        return self._encode(user.id, _TokenType.REFRESH, self._refresh_ttl)

    def verify_access_token(self, token: str) -> uuid.UUID:
        return self._decode(token, _TokenType.ACCESS)

    def verify_refresh_token(self, token: str) -> uuid.UUID:
        return self._decode(token, _TokenType.REFRESH)

    def _encode(
        self, user_id: uuid.UUID, token_type: _TokenType, ttl: timedelta
    ) -> str:
        payload = {
            "sub": str(user_id),
            "type": token_type.value,
            "exp": datetime.now(UTC) + ttl,
        }
        return jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)

    def _decode(self, token: str, expected_type: _TokenType) -> uuid.UUID:
        try:
            payload = jwt.decode(
                token, self._jwt_secret, algorithms=[self._jwt_algorithm]
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTokenError("expired") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError("malformed") from exc

        if payload.get("type") != expected_type.value:
            raise InvalidTokenError(f"expected a {expected_type.value} token")

        try:
            return uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise InvalidTokenError("missing or invalid subject") from exc
