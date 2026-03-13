import pytest

from fair_platform.backend.services.email_provider import ConsoleEmailProvider


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
