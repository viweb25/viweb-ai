import logging
from secrets import token_urlsafe

from vi_api.app.identity.sign_in import token_hash
from vi_api.domain.errors import InvalidInput, PermissionDenied, Unavailable
from vi_api.domain.identity.account_links import AccountLinkMail, AccountLinkRepository
from vi_api.domain.identity.models import Membership
from vi_api.domain.identity.ports import IdentityRepository, PasswordHasher, SignInRateLimited

logger = logging.getLogger(__name__)


class AccountLinks:
    def __init__(
        self, links: AccountLinkRepository, identity: IdentityRepository,
        passwords: PasswordHasher, mail: AccountLinkMail,
    ):
        self.links = links
        self.identity = identity
        self.passwords = passwords
        self.mail = mail

    async def invite(self, member: Membership, email: str, role: str) -> None:
        if member.role not in ("owner", "admin"):
            raise PermissionDenied("Only workspace owners and admins can invite teammates")
        if role not in ("operator", "viewer"):
            raise InvalidInput("Choose an operator or viewer role")
        self._require_mail()
        email = email.strip().lower()
        token = token_urlsafe(32)
        await self.links.invite(member.org_id, email, role, token_hash(token))
        try:
            await self.mail.send_invite(email, token)
        except (OSError, ValueError) as exc:
            raise Unavailable("The invitation email could not be sent. Try again.") from exc

    async def accept(self, token: str, password: str | None, source: str) -> None:
        await self._limit(f"invite-accept:{source}", 30)
        password_hash = await self.passwords.hash(password) if password else None
        await self.links.accept(token_hash(token), password_hash)

    async def request_reset(self, email: str, source: str) -> tuple[str, str] | None:
        self._require_mail()
        email = email.strip().lower()
        await self._limit(f"reset-source:{source}", 30)
        if await self.identity.record_sign_in_attempt(token_hash(f"reset-email:{email}")) > 3:
            return None
        token = token_urlsafe(32)
        if await self.links.request_reset(email, token_hash(token)):
            return email, token
        return None

    async def deliver_reset(self, email: str, token: str) -> None:
        try:
            await self.mail.send_reset(email, token)
        except (OSError, ValueError):
            logger.warning("Password recovery email delivery failed")

    def _require_mail(self) -> None:
        if not self.mail.configured:
            raise Unavailable("Account email is unavailable. Contact your workspace administrator.")

    async def reset(self, token: str, password: str, source: str) -> None:
        await self._limit(f"reset-complete:{source}", 30)
        await self.links.reset(token_hash(token), await self.passwords.hash(password))

    async def _limit(self, bucket: str, maximum: int) -> None:
        if await self.identity.record_sign_in_attempt(token_hash(bucket)) > maximum:
            raise SignInRateLimited
