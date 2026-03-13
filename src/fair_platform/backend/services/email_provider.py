from __future__ import annotations

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


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
