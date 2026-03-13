from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from fair_platform.backend.services.email_provider import (
    ConsoleEmailProvider,
    EmailProvider,
)


def _resolve_email_templates_dir() -> Path:
    module_path = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "src" / "templates" / "emails",
        module_path.parents[4] / "templates" / "emails",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise RuntimeError("Email templates directory not found")


def create_email_template_environment() -> Environment:
    template_dir = _resolve_email_templates_dir()
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(default_for_string=True, enabled_extensions=("html", "xml")),
    )


class Mailer:
    def __init__(self, provider: EmailProvider, template_env: Environment):
        self.provider = provider
        self.template_env = template_env

    async def send_password_reset(self, user: Any, reset_url: str) -> None:
        template = self.template_env.get_template("forgot_password.html")
        html_content = template.render(user=user, reset_url=reset_url)
        await self.provider.send_email(
            to=str(user.email),
            subject="Reset your FAIR password",
            html_content=html_content,
        )

    async def send_verification(self, user: Any, verification_url: str) -> None:
        template = self.template_env.get_template("verify_email.html")
        html_content = template.render(user=user, verification_url=verification_url)
        await self.provider.send_email(
            to=str(user.email),
            subject="Verify your FAIR account",
            html_content=html_content,
        )


def get_mailer() -> Mailer:
    return Mailer(
        provider=ConsoleEmailProvider(),
        template_env=create_email_template_environment(),
    )
