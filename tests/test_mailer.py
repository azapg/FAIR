from types import SimpleNamespace

from fair_platform.backend.services.email_provider import (
    ConsoleEmailProvider,
    ResendEmailProvider,
)
from fair_platform.backend.services.mailer import (
    _resolve_email_templates_dir,
    create_email_template_environment,
    get_mailer,
)


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


def test_resolve_email_templates_dir_contains_expected_templates() -> None:
    templates_dir = _resolve_email_templates_dir()
    assert (templates_dir / "forgot_password.html").is_file()
    assert (templates_dir / "verify_email.html").is_file()


def test_email_templates_render_expected_variables() -> None:
    template_env = create_email_template_environment()
    user = SimpleNamespace(name="Ada")

    forgot_html = template_env.get_template("forgot_password.html").render(
        user=user, reset_url="https://example.com/reset"
    )
    assert "Ada" in forgot_html
    assert "https://example.com/reset" in forgot_html

    verify_html = template_env.get_template("verify_email.html").render(
        user=user, verification_url="https://example.com/verify"
    )
    assert "Ada" in verify_html
    assert "https://example.com/verify" in verify_html
