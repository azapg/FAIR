import pytest

from fair_platform.backend.core.releases import EXPERIMENTAL_FEATURES


@pytest.fixture(autouse=True)
def release_environment(monkeypatch):
    monkeypatch.delenv("FAIR_RELEASE_CHANNEL", raising=False)
    for feature in EXPERIMENTAL_FEATURES:
        monkeypatch.delenv(f"FAIR_FEATURE_{feature.upper()}", raising=False)


def config(client):
    response = client.get("/api/v1/system/config")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("channel", [None, "stable", "canary", "typo"])
def test_stable_is_the_safe_default(test_client, monkeypatch, channel):
    if channel is not None:
        monkeypatch.setenv("FAIR_RELEASE_CHANNEL", channel)
    for feature in EXPERIMENTAL_FEATURES:
        monkeypatch.setenv(f"FAIR_FEATURE_{feature.upper()}", "true")
    data = config(test_client)
    assert data["release_channel"] == "stable"
    assert all(data["features"][feature] is False for feature in EXPERIMENTAL_FEATURES)
    assert "registration" in data
    assert "email_enabled" in data["features"]


def test_nightly_exposes_experiments(test_client, monkeypatch):
    monkeypatch.setenv("FAIR_RELEASE_CHANNEL", " Nightly ")
    data = config(test_client)
    assert data["release_channel"] == "nightly"
    assert all(data["features"][feature] is True for feature in EXPERIMENTAL_FEATURES)


@pytest.mark.parametrize("feature", EXPERIMENTAL_FEATURES)
def test_nightly_features_can_be_disabled_independently(
    test_client, monkeypatch, feature
):
    monkeypatch.setenv("FAIR_RELEASE_CHANNEL", "nightly")
    monkeypatch.setenv(f"FAIR_FEATURE_{feature.upper()}", "false")
    data = config(test_client)
    assert data["features"][feature] is False
    assert all(
        data["features"][other] is True
        for other in EXPERIMENTAL_FEATURES
        if other != feature
    )
