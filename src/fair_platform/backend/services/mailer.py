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

    async def send_password_reset(self, user: Any, token: str) -> None:
        template = self.template_env.get_template("forgot_password.html")
        html_content = template.render(user=user, token=token)
        await self.provider.send_email(
            to=str(user.email),
            subject="Reset your FAIR password",
            html_content=html_content,
        )

    async def send_verification(self, user: Any, token: str) -> None:
        verification_url = f"https://example.invalid/verify?token={token}"
        html_content = (
            "<h1>Verify your email</h1>"
            f"<p>Hello {user.name}, use this token to verify your account: <code>{token}</code>.</p>"
            f"<p>Verification link: <a href=\"{verification_url}\">{verification_url}</a></p>"
        )
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
