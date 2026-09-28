from fastapi import APIRouter, Cookie, Response

from rag.api.deps import AuthServiceDep, CurrentUserDep, SettingsDep
from rag.api.schema.auth import LoginRequest, TokenResponse, UserResponse
from rag.config import Settings
from rag.domain.errors import InvalidTokenError

_REFRESH_COOKIE = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/auth"

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        max_age=settings.AUTH.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
    )


@router.post("/login")
async def login(
    login_request: LoginRequest,
    response: Response,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> TokenResponse:
    user = await auth_service.authenticate(login_request.email, login_request.password)
    _set_refresh_cookie(response, auth_service.create_refresh_token(user), settings)
    return TokenResponse(access_token=auth_service.create_access_token(user))


@router.post("/refresh")
async def refresh(
    auth_service: AuthServiceDep,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> TokenResponse:
    if refresh_token is None:
        raise InvalidTokenError("missing refresh cookie")
    user_id = auth_service.verify_refresh_token(refresh_token)
    user = await auth_service.get_user(user_id)
    return TokenResponse(access_token=auth_service.create_access_token(user))


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path=_REFRESH_COOKIE_PATH)


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserResponse:
    return UserResponse(
        id=current_user.id, email=current_user.email, is_admin=current_user.is_admin
    )
