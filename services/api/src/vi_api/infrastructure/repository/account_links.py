from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from vi_api.domain.errors import Conflict, InvalidInput, NotFound


class PostgresAccountLinks:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def invite(self, org_id: UUID, email: str, role: str, token_hash: bytes) -> None:
        async with self.sessions.begin() as session:
            await session.execute(text("""
                INSERT INTO identity.workspace_invitations
                    (org_id, email, role, token_hash, expires_at)
                VALUES (:org, :email, :role, :token, now() + interval '48 hours')
                ON CONFLICT (org_id, email) DO UPDATE SET
                    role = EXCLUDED.role, token_hash = EXCLUDED.token_hash,
                    expires_at = EXCLUDED.expires_at
            """), {"org": org_id, "email": email, "role": role, "token": token_hash})

    async def accept(self, token_hash: bytes, password_hash: str | None) -> None:
        try:
            async with self.sessions.begin() as session:
                result = await session.execute(text("""
                    DELETE FROM identity.workspace_invitations
                    WHERE token_hash = :token AND expires_at > now()
                    RETURNING org_id, email, role
                """), {"token": token_hash})
                invite = result.mappings().one_or_none()
                if invite is None:
                    raise NotFound("This invitation has expired or was already used")
                user_id = await session.scalar(text("""
                    SELECT user_id FROM identity.password_credentials WHERE email = :email
                """), {"email": invite["email"]})
                if user_id is None:
                    if not password_hash:
                        raise InvalidInput(
                            "Set a password for your new account", "password_required"
                        )
                    user_id = await session.scalar(text("""
                        INSERT INTO identity.users (email) VALUES (:email) RETURNING id
                    """), {"email": invite["email"]})
                    await session.execute(text("""
                        INSERT INTO identity.password_credentials (user_id, email, password_hash)
                        VALUES (:id, :email, :password)
                    """), {"id": user_id, "email": invite["email"], "password": password_hash})
                await session.execute(text("""
                    INSERT INTO identity.memberships (org_id, user_id, role)
                    VALUES (:org, :user, :role)
                    ON CONFLICT (org_id, user_id) DO UPDATE
                    SET status = 'active', role = EXCLUDED.role
                    WHERE identity.memberships.status = 'revoked'
                      AND identity.memberships.role IN ('operator', 'viewer')
                """), {"org": invite["org_id"], "user": user_id, "role": invite["role"]})
        except IntegrityError as exc:
            raise Conflict("The account changed. Open the invitation and try again.") from exc

    async def request_reset(self, email: str, token_hash: bytes) -> bool:
        async with self.sessions.begin() as session:
            user_id = await session.scalar(text("""
                INSERT INTO identity.password_resets (user_id, token_hash, expires_at)
                SELECT p.user_id, :token, now() + interval '30 minutes'
                FROM identity.password_credentials p JOIN identity.users u ON u.id = p.user_id
                WHERE p.email = :email AND u.status = 'active'
                ON CONFLICT (user_id) DO UPDATE SET token_hash = EXCLUDED.token_hash,
                    expires_at = EXCLUDED.expires_at
                RETURNING user_id
            """), {"email": email, "token": token_hash})
        return user_id is not None

    async def reset(self, token_hash: bytes, password_hash: str) -> None:
        async with self.sessions.begin() as session:
            user_id = await session.scalar(text("""
                DELETE FROM identity.password_resets
                WHERE token_hash = :token AND expires_at > now() RETURNING user_id
            """), {"token": token_hash})
            if user_id is None:
                raise NotFound("This recovery link has expired or was already used")
            await session.execute(text("""
                UPDATE identity.password_credentials SET password_hash = :password
                WHERE user_id = :user
            """), {"user": user_id, "password": password_hash})
            await session.execute(text("""
                UPDATE identity.sessions SET revoked_at = now()
                WHERE user_id = :user AND revoked_at IS NULL
            """), {"user": user_id})
