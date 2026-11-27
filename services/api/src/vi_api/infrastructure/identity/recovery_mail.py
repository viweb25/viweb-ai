import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from vi_api.config.settings import Settings


class SmtpAccountMail:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.smtp_host and self.settings.smtp_from)

    async def send_invite(self, email: str, token: str) -> None:
        await asyncio.to_thread(
            self._send, email, "Join a Vision Studio workspace",
            f"Accept your invitation within 48 hours:\n\n{self._link('invite', token)}",
        )

    async def send_reset(self, email: str, token: str) -> None:
        await asyncio.to_thread(
            self._send, email, "Reset your Vision Studio password",
            f"Reset your password within 30 minutes:\n\n{self._link('reset', token)}",
        )

    def _link(self, action: str, token: str) -> str:
        return f"{self.settings.app_origin.rstrip('/')}/{action}#{token}"

    def _send(self, email: str, subject: str, content: str) -> None:
        settings = self.settings
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = email
        message.set_content(content)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
            server.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            server.send_message(message)
