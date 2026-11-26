from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

EMAIL_VISIBLE_ROLES = frozenset({"owner", "admin"})


@dataclass(frozen=True)
class WorkspaceMember:
    id: UUID
    name: str
    role: str


class WorkspaceRepository(Protocol):
    async def list_members(self, org_id: UUID, include_email: bool) -> list[WorkspaceMember]: ...


def can_see_member_emails(role: str) -> bool:
    return role in EMAIL_VISIBLE_ROLES
