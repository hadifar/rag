from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Response

from rag.api.deps import AuthServiceDep, CurrentUserDep
from rag.api.schema.auth import LoginRequest, TokenResponse, UserResponse

_REFRESH_COOKIE = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/auth"

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str, ttl: timedelta) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        max_age=int(ttl.total_seconds()),
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
    )


@router.post("/login")
async def login(
    login_request: LoginRequest,
    http_response: Response,
    auth_service: AuthServiceDep,
) -> TokenResponse:

    user = await auth_service.authenticate(login_request.email, login_request.password)

    _set_refresh_cookie(
        http_response, auth_service.create_refresh_token(user), auth_service.refresh_ttl
    )

    return TokenResponse(access_token=auth_service.create_access_token(user))


@router.post("/refresh")
async def refresh(
    auth_service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE)] = None,
) -> TokenResponse:
    user_id = auth_service.verify_refresh_token(refresh_token)
    user = await auth_service.get_user(user_id)
    return TokenResponse(access_token=auth_service.create_access_token(user))


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path=_REFRESH_COOKIE_PATH)


@router.get("/me")
async def me(
    current_user: CurrentUserDep, auth_service: AuthServiceDep
) -> UserResponse:
    user = await auth_service.get_user(current_user.id)
    return UserResponse.model_validate(user)
