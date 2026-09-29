import uuid
from datetime import timedelta

import pytest

from rag.domain.errors import (
    AdminRequiredError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserEmailNotFoundError,
    UserNotFoundError,
)
from rag.services.auth_service.service import AuthenticatedIdentity, AuthService
from tests.unit.fakes import FakeUserRepository


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(
        user_repository=FakeUserRepository(),
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


async def test_users_are_not_admins_unless_created_as_one(
    auth_service: AuthService,
) -> None:
    user = await auth_service.create_user("a@example.com", "correct horse")
    admin = await auth_service.create_user("b@example.com", "pw", is_admin=True)

    assert not user.is_admin
    assert admin.is_admin


async def test_set_admin_grants_and_revokes(auth_service: AuthService) -> None:
    await auth_service.create_user("a@example.com", "correct horse")

    assert (await auth_service.set_admin("a@example.com", True)).is_admin
    assert not (await auth_service.set_admin("a@example.com", False)).is_admin


async def test_set_admin_unknown_email_raises(auth_service: AuthService) -> None:
    with pytest.raises(UserEmailNotFoundError):
        await auth_service.set_admin("nobody@example.com", True)


async def test_require_admin_rejects_non_admins(auth_service: AuthService) -> None:
    user = await auth_service.create_user("a@example.com", "correct horse")
    identity = AuthenticatedIdentity(id=user.id, is_admin=user.is_admin)

    with pytest.raises(AdminRequiredError):
        AuthService.require_admin(identity)
