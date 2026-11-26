from vi_api.domain.identity.ports import AccountRepository, PasswordHasher


class SignUp:
    """Create a new workspace with the signing-up user as its owner."""

    def __init__(self, accounts: AccountRepository, passwords: PasswordHasher):
        self.accounts = accounts
        self.passwords = passwords

    async def execute(self, email: str, password: str, organisation: str) -> None:
        password_hash = await self.passwords.hash(password)
        await self.accounts.provision_owner(
            email.strip().lower(), organisation.strip(), password_hash
        )
