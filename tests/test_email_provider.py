import logging

import pytest
import resend

from fair_platform.backend.services.email_provider import (
    ConsoleEmailProvider,
    ResendEmailProvider,
)


@pytest.mark.asyncio
async def test_console_email_provider_writes_payload_to_stdout(capsys) -> None:
    provider = ConsoleEmailProvider()
    await provider.send_email(
        to="student@example.com",
        subject="Reset your FAIR password",
        html_content="<p>Hello</p>",
    )

    captured = capsys.readouterr()
    assert "=== FAIR EMAIL ===" in captured.out
    assert "To: student@example.com" in captured.out
    assert "Subject: Reset your FAIR password" in captured.out
    assert "<p>Hello</p>" in captured.out


@pytest.mark.asyncio
async def test_resend_email_provider_dispatches_payload(monkeypatch) -> None:
    payloads: list[dict] = []

    def fake_send(payload: dict) -> None:
        payloads.append(payload)

    monkeypatch.setattr(resend.Emails, "send", fake_send)
    monkeypatch.setattr(resend, "api_key", None)
    provider = ResendEmailProvider(
        api_key="re_test_123",
        sender="FairGrade Platform <noreply@fairgradeproject.org>",
    )

    await provider.send_email(
        to="student@example.com",
        subject="Verify your FAIR account",
        html_content="<p>Verify</p>",
    )

    assert resend.api_key == "re_test_123"
    assert payloads == [
        {
            "from": "FairGrade Platform <noreply@fairgradeproject.org>",
            "to": "student@example.com",
            "subject": "Verify your FAIR account",
            "html": "<p>Verify</p>",
        }
    ]


@pytest.mark.asyncio
async def test_resend_email_provider_raises_runtime_error_on_api_error(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = ResendEmailProvider(api_key="re_test_123")
    caplog.set_level(logging.ERROR)

    def fake_send(_payload: dict) -> None:
        raise resend.exceptions.ValidationError(
            message="boom",
            error_type="validation_error",
            code=400,
        )

    monkeypatch.setattr(resend.Emails, "send", fake_send)

    with pytest.raises(RuntimeError, match="Failed to send email with Resend"):
        await provider.send_email(
            to="student@example.com",
            subject="Reset",
            html_content="<p>Reset</p>",
        )

    assert "Failed to send email with Resend" in caplog.text
