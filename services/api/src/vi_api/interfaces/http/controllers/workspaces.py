from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from vi_api.app.workspaces.workspace_service import WorkspaceService
from vi_api.container import get_workspace_service
from vi_api.interfaces.http.dependencies.identity import OrgMember

router = APIRouter(prefix="/api/v1/organisations", tags=["Workspaces"])
Workspaces = Annotated[WorkspaceService, Depends(get_workspace_service)]


class WorkspaceMember(BaseModel):
    id: UUID
    name: str
    role: str


@router.get("/{org_id}/members")
async def list_members(
    member: OrgMember, service: Workspaces, response: Response
) -> list[WorkspaceMember]:
    response.headers["Cache-Control"] = "no-store"
    members = await service.list_members(member)
    return [WorkspaceMember.model_validate(asdict(item)) for item in members]
