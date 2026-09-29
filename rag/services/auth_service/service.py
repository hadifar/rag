import asyncio
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
from rag.domain.models import AuthenticatedIdentity, User
from rag.domain.ports import UserRepositoryPort


class _TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class AuthService:
    """Password hashing runs in a thread: argon2 is slow on purpose, and on the event
    loop it would stall every other request, including open chat streams.
    """

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
        hashed_password = await asyncio.to_thread(self._hasher.hash, password)
        return await self._user_repository.create(
            _normalize_email(email), hashed_password, is_admin=is_admin
        )

    async def set_admin(self, email: str, is_admin: bool) -> User:
        user = await self._user_repository.set_admin(_normalize_email(email), is_admin)
        if user is None:
            raise UserEmailNotFoundError(email)
        return user

    @staticmethod
    def require_admin(identity: AuthenticatedIdentity) -> AuthenticatedIdentity:
        if not identity.is_admin:
            raise AdminRequiredError()
        return identity

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._user_repository.get_by_email(_normalize_email(email))
        if user is None:
            raise InvalidCredentialsError()
        try:
            await asyncio.to_thread(self._hasher.verify, user.hashed_password, password)
        except VerifyMismatchError as exc:
            raise InvalidCredentialsError() from exc
        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def authenticate_access_token(self, token: str) -> AuthenticatedIdentity:
        user = await self.get_user(self.verify_access_token(token))
        return AuthenticatedIdentity(id=user.id, is_admin=user.is_admin)

    @property
    def refresh_ttl(self) -> timedelta:
        return self._refresh_ttl

    def create_access_token(self, user: User) -> str:
        return self._encode(user.id, _TokenType.ACCESS, self._access_ttl)

    def create_refresh_token(self, user: User) -> str:
        return self._encode(user.id, _TokenType.REFRESH, self._refresh_ttl)

    def verify_access_token(self, token: str) -> uuid.UUID:
        return self._decode(token, _TokenType.ACCESS)

    def verify_refresh_token(self, token: str | None) -> uuid.UUID:
        if token is None:
            raise InvalidTokenError("missing refresh cookie")
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


def _normalize_email(email: str) -> str:
    """Emails are stored lowercase (the users table checks it), so `Ann@x.com` and
    `ann@x.com` are one account and either one logs in.
    """
    return email.strip().lower()
