from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from pydantic import BaseModel, Field, SecretStr

from vi_api.app.identity.account_links import AccountLinks
from vi_api.app.identity.sign_in import SignIn, token_hash
from vi_api.app.identity.sign_up import SignUp
from vi_api.container import get_account_links, get_sign_in, get_sign_up
from vi_api.domain.identity.models import CurrentUser
from vi_api.domain.identity.ports import SignInRateLimited, SignInRejected
from vi_api.interfaces.http.auth_configuration import cookie_name
from vi_api.interfaces.http.dependencies.identity import (
    SESSION_COOKIE,
    BrowserOrigin,
    IdentityRepo,
    SessionToken,
    get_current_user,
)
from vi_api.interfaces.http.errors import ApiError, ErrorCode
from vi_api.interfaces.http.schemas.account_links import (
    AcceptInvitation,
    RecoveryRequest,
    ResetPassword,
)
from vi_api.interfaces.http.schemas.errors import ErrorResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Identity"])
SESSION_TTL = 8 * 60 * 60
SignInDependency = Annotated[SignIn, Depends(get_sign_in)]
SignUpDependency = Annotated[SignUp, Depends(get_sign_up)]
Links = Annotated[AccountLinks, Depends(get_account_links)]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+$")
    password: SecretStr = Field(min_length=1, max_length=128)


class SignupRequest(LoginRequest):
    password: SecretStr = Field(min_length=15, max_length=128)
    organisation: str = Field(min_length=1, max_length=200, pattern=r"\S")


def account_link_source(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/invitations/accept", status_code=204)
async def accept_invitation(
    data: AcceptInvitation, request: Request, service: Links, _: BrowserOrigin,
) -> None:
    try:
        await service.accept(
            data.token.get_secret_value(),
            data.password.get_secret_value() if data.password else None,
            account_link_source(request),
        )
    except SignInRateLimited as exc:
        raise ApiError(
            429, ErrorCode.SIGN_IN_RATE_LIMITED, "Too many attempts. Try again later."
        ) from exc


@router.post("/password/recovery", status_code=204)
async def request_password_recovery(
    data: RecoveryRequest, request: Request, background: BackgroundTasks,
    service: Links, _: BrowserOrigin,
) -> None:
    try:
        delivery = await service.request_reset(data.email, account_link_source(request))
    except SignInRateLimited as exc:
        raise ApiError(
            429, ErrorCode.SIGN_IN_RATE_LIMITED, "Too many attempts. Try again later."
        ) from exc
    if delivery:
        background.add_task(service.deliver_reset, *delivery)


@router.post("/password/reset", status_code=204)
async def reset_password(
    data: ResetPassword, request: Request, service: Links, _: BrowserOrigin,
) -> None:
    try:
        await service.reset(
            data.token.get_secret_value(), data.password.get_secret_value(),
            account_link_source(request),
        )
    except SignInRateLimited as exc:
        raise ApiError(
            429, ErrorCode.SIGN_IN_RATE_LIMITED, "Too many attempts. Try again later."
        ) from exc


@router.post(
    "/signup",
    status_code=204,
    responses={code: {"model": ErrorResponse} for code in (403, 409)},
)
async def signup(
    credentials: SignupRequest, sign_up: SignUpDependency, origin: BrowserOrigin
) -> None:
    await sign_up.execute(
        credentials.email, credentials.password.get_secret_value(), credentials.organisation
    )


@router.post(
    "/login",
    status_code=204,
    responses={code: {"model": ErrorResponse} for code in (401, 403, 429)},
)
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    sign_in: SignInDependency,
    origin: BrowserOrigin,
    previous_session: SessionToken = None,
) -> None:
    source = request.client.host if request.client else "unknown"
    try:
        token = await sign_in.execute(
            credentials.email, credentials.password.get_secret_value(), source, previous_session
        )
    except SignInRateLimited as exc:
        raise ApiError(
            429, ErrorCode.SIGN_IN_RATE_LIMITED, "Too many attempts. Try again later."
        ) from exc
    except SignInRejected as exc:
        raise ApiError(
            401, ErrorCode.INVALID_CREDENTIALS, "Email or password is incorrect"
        ) from exc
    secure = origin.startswith("https:")
    response.set_cookie(
        cookie_name(SESSION_COOKIE, secure),
        token,
        max_age=SESSION_TTL,
        secure=secure,
        httponly=True,
        samesite="strict",
        path="/",
    )


@router.get("/me", responses={401: {"model": ErrorResponse}})
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    return user


@router.post("/logout", status_code=204, responses={403: {"model": ErrorResponse}})
async def logout(
    response: Response,
    repository: IdentityRepo,
    origin: BrowserOrigin,
    token: SessionToken = None,
) -> None:
    if token:
        await repository.revoke_session(token_hash(token))
    secure = origin.startswith("https:")
    response.delete_cookie(
        cookie_name(SESSION_COOKIE, secure), secure=secure, httponly=True, samesite="strict"
    )
