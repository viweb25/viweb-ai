from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr

AccountEmail = Annotated[
    str, Field(min_length=3, max_length=254, pattern=r"^[A-Za-z0-9._%+!-]+@[A-Za-z0-9.-]+$")
]
LinkToken = Annotated[SecretStr, Field(min_length=43, max_length=43)]
NewPassword = Annotated[SecretStr, Field(min_length=15, max_length=128)]


class InvitationRequest(BaseModel):
    email: AccountEmail
    role: Literal["operator", "viewer"]


class AcceptInvitation(BaseModel):
    token: LinkToken
    password: NewPassword | None = None


class RecoveryRequest(BaseModel):
    email: AccountEmail


class ResetPassword(BaseModel):
    token: LinkToken
    password: NewPassword
