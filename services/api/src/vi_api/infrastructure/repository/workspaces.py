from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from vi_api.domain.workspaces.models import WorkspaceMember


class PostgresWorkspaceRepository:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def list_members(self, org_id: UUID, include_email: bool) -> list[WorkspaceMember]:
        async with self.sessions() as session:
            rows = await session.execute(
                text("""
                    SELECT u.id, COALESCE(NULLIF(u.display_name, ''),
                        CASE WHEN :include_email THEN u.email END, 'Workspace member') AS name,
                        m.role
                    FROM identity.memberships m JOIN identity.users u ON u.id = m.user_id
                    WHERE m.org_id = :org AND m.status = 'active' AND u.status = 'active'
                    ORDER BY m.created_at, u.id
                """),
                {"org": org_id, "include_email": include_email},
            )
            return [WorkspaceMember(**row) for row in rows.mappings()]
