from __future__ import annotations

from abc import ABC, abstractmethod
import logging

import resend

logger = logging.getLogger(__name__)
DEFAULT_EMAIL_SENDER = "FairGrade Platform <noreply@fairgradeproject.org>"
RESEND_API_ERROR = getattr(
    resend.exceptions,
    "APIError",
    resend.exceptions.ResendError,
)


class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, to: str, subject: str, html_content: str) -> None:
        """Send an HTML email message to a recipient."""


class ConsoleEmailProvider(EmailProvider):
    async def send_email(self, to: str, subject: str, html_content: str) -> None:
        payload = (
            "\n=== FAIR EMAIL ===\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            "Content-Type: text/html\n"
            "--- HTML ---\n"
            f"{html_content}\n"
            "=== END EMAIL ===\n"
        )
        print(payload, flush=True)
        logger.info(
            "EMAIL to=%s subject=%s html_content=%s",
            to,
            subject,
            html_content,
        )


class ResendEmailProvider(EmailProvider):
    def __init__(
        self,
        *,
        api_key: str,
        sender: str = DEFAULT_EMAIL_SENDER,
    ) -> None:
        self.api_key = api_key
        self.sender = sender

    async def send_email(self, to: str, subject: str, html_content: str) -> None:
        resend.api_key = self.api_key
        payload = {
            "from": self.sender,
            "to": to,
            "subject": subject,
            "html": html_content,
        }
        try:
            resend.Emails.send(payload)
        except RESEND_API_ERROR as exc:
            logger.exception(
                "Failed to send email with Resend to=%s subject=%s",
                to,
                subject,
            )
            raise RuntimeError("Failed to send email with Resend") from exc
