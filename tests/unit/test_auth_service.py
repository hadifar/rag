import uuid
from datetime import UTC, datetime, timedelta

import pytest

from rag.domain.errors import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from rag.domain.models import User
from rag.services.auth_service.service import AuthService


class _FakeUserRepository:
    def __init__(self):
        self._users: dict[uuid.UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(user_id)

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.now(UTC),
        )
        self._users[user.id] = user
        return user


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(
        user_repository=_FakeUserRepository(),
        jwt_secret="test-secret-that-is-long-enough-32b",
        jwt_algorithm="HS256",
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


async def test_create_and_authenticate_user(auth_service: AuthService) -> None:
    user = await auth_service.create_user("a@example.com", "correct horse")

    authenticated = await auth_service.authenticate("a@example.com", "correct horse")

    assert authenticated.id == user.id
    assert authenticated.hashed_password != "correct horse"  # actually hashed


async def test_authenticate_wrong_password_raises(auth_service: AuthService) -> None:
    await auth_service.create_user("a@example.com", "correct horse")

    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate("a@example.com", "wrong password")


async def test_authenticate_unknown_email_raises(auth_service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate("nobody@example.com", "anything")


async def test_access_token_round_trips_to_user_id(auth_service: AuthService) -> None:
    user = await auth_service.create_user("a@example.com", "correct horse")

    token = auth_service.create_access_token(user)

    assert auth_service.verify_access_token(token) == user.id


async def test_refresh_token_rejected_as_access_token(
    auth_service: AuthService,
) -> None:
    user = await auth_service.create_user("a@example.com", "correct horse")

    refresh_token = auth_service.create_refresh_token(user)

    with pytest.raises(InvalidTokenError):
        auth_service.verify_access_token(refresh_token)


async def test_garbage_token_raises_invalid_token_error(
    auth_service: AuthService,
) -> None:
    with pytest.raises(InvalidTokenError):
        auth_service.verify_access_token("not-a-jwt")


async def test_get_user_missing_raises_user_not_found(
    auth_service: AuthService,
) -> None:
    with pytest.raises(UserNotFoundError):
        await auth_service.get_user(uuid.uuid4())
