"""HTTP endpoints for authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth import rate_limit, service
from app.auth.dependencies import AuthUser, get_current_user
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    PlatformLoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserSummary,
)
from app.auth.security import blacklist_access_token, hash_refresh_token
from app.config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _tokens(result: service.AuthResult) -> TokenResponse:
    return TokenResponse(
        user=UserSummary(id=result.user_id, email=result.email, role=result.role),
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
        scope=result.scope,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register into an existing tenant",
)
async def register(body: RegisterRequest, request: Request) -> TokenResponse:
    settings = get_settings()
    await rate_limit.enforce(
        request.app.state.redis,
        key=f"sb:rl:register:{rate_limit.client_ip(request)}",
        limit=settings.register_limit,
        window_seconds=settings.register_window_seconds,
    )
    result = await service.register(
        request.app.state.sessionmaker,
        tenant_slug=body.tenant_slug,
        email=str(body.email),
        password=body.password,
        display_name=body.display_name,
        ip=rate_limit.client_ip(request),
    )
    return _tokens(result)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in to a tenant",
)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    settings = get_settings()
    await rate_limit.enforce(
        request.app.state.redis,
        key=f"sb:rl:login:{body.tenant_slug.lower()}:{str(body.email).lower()}",
        limit=settings.login_limit,
        window_seconds=settings.login_window_seconds,
    )
    result = await service.login(
        request.app.state.sessionmaker,
        tenant_slug=body.tenant_slug,
        email=str(body.email),
        password=body.password,
        ip=rate_limit.client_ip(request),
    )
    return _tokens(result)


@router.post(
    "/platform-login",
    response_model=TokenResponse,
    summary="Log in as a platform operator (no tenant)",
)
async def platform_login(body: PlatformLoginRequest, request: Request) -> TokenResponse:
    settings = get_settings()
    await rate_limit.enforce(
        request.app.state.redis,
        key=f"sb:rl:platform-login:{str(body.email).lower()}",
        limit=settings.login_limit,
        window_seconds=settings.login_window_seconds,
    )
    result = await service.platform_login(
        request.app.state.sessionmaker,
        email=str(body.email),
        password=body.password,
        ip=rate_limit.client_ip(request),
    )
    return _tokens(result)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate a refresh token",
)
async def refresh(body: RefreshRequest, request: Request) -> TokenResponse:
    settings = get_settings()
    digest = hash_refresh_token(body.refresh_token).hex()[:16]
    await rate_limit.enforce(
        request.app.state.redis,
        key=f"sb:rl:refresh:{digest}",
        limit=settings.refresh_limit,
        window_seconds=settings.refresh_window_seconds,
    )
    result = await service.refresh(
        request.app.state.sessionmaker,
        token=body.refresh_token,
        ip=rate_limit.client_ip(request),
    )
    return _tokens(result)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out and optionally revoke the refresh family",
)
async def logout(
    request: Request,
    body: LogoutRequest | None = None,
    user: AuthUser = Depends(get_current_user),
) -> Response:
    await blacklist_access_token(request.app.state.redis, user.jti, user.exp)
    await service.logout(
        request.app.state.sessionmaker,
        user_id=user.id,
        family_id=user.family_id,
        all_sessions=bool(body and body.all_sessions),
        ip=rate_limit.client_ip(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
