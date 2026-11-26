from uuid import UUID

from sqlalchemy.exc import IntegrityError

from vi_api.domain.errors import Conflict
from vi_api.infrastructure.identity.provision_owner import provision_owner


class PostgresAccountRepository:
    async def provision_owner(
        self, email: str, organisation: str, password_hash: str
    ) -> tuple[UUID, UUID]:
        try:
            return await provision_owner(email, organisation, password_hash)
        except IntegrityError as exc:
            raise Conflict("An account already uses this email", "signup_conflict") from exc
