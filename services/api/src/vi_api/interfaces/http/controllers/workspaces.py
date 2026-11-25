from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text

from vi_api.domain.identity.models import Membership
from vi_api.infrastructure.database.session import Session
from vi_api.interfaces.http.dependencies.identity import require_organisation_access

router = APIRouter(prefix="/api/v1/organisations", tags=["Workspaces"])


class WorkspaceMember(BaseModel):
    id: UUID
    name: str
    role: str


@router.get("/{org_id}/members")
async def list_members(
    member: Annotated[Membership, Depends(require_organisation_access)],
    response: Response,
) -> list[WorkspaceMember]:
    response.headers["Cache-Control"] = "no-store"
    async with Session() as session:
        rows = await session.execute(
            text("""
                SELECT u.id, COALESCE(NULLIF(u.display_name, ''),
                    CASE WHEN :include_email THEN u.email END, 'Workspace member') AS name,
                    m.role
                FROM identity.memberships m JOIN identity.users u ON u.id = m.user_id
                WHERE m.org_id = :org AND m.status = 'active' AND u.status = 'active'
                ORDER BY m.created_at, u.id
            """),
            {"org": member.org_id, "include_email": member.role in {"owner", "admin"}},
        )
        return [WorkspaceMember.model_validate(dict(row)) for row in rows.mappings()]
