from vi_api.domain.identity.models import Membership
from vi_api.domain.workspaces.models import (
    WorkspaceMember,
    WorkspaceRepository,
    can_see_member_emails,
)


class WorkspaceService:
    def __init__(self, workspaces: WorkspaceRepository):
        self.workspaces = workspaces

    async def list_members(self, member: Membership) -> list[WorkspaceMember]:
        return await self.workspaces.list_members(
            member.org_id, include_email=can_see_member_emails(member.role)
        )
