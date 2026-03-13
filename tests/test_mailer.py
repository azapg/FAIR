from fair_platform.backend.services.email_provider import (
    ConsoleEmailProvider,
    ResendEmailProvider,
)
from fair_platform.backend.services.mailer import get_mailer


def test_get_mailer_uses_console_provider_without_resend_key(monkeypatch) -> None:
    monkeypatch.delenv("FAIR_RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    mailer = get_mailer()
    assert isinstance(mailer.provider, ConsoleEmailProvider)


def test_get_mailer_uses_resend_provider_with_resend_key(monkeypatch) -> None:
    monkeypatch.delenv("FAIR_RESEND_API_KEY", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "re_live_example")
    mailer = get_mailer()
    assert isinstance(mailer.provider, ResendEmailProvider)
    assert mailer.provider.api_key == "re_live_example"
