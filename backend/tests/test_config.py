import pytest

from app.config import ConfigError, load_settings


def _base_env(monkeypatch):
    for k, v in {
        "DATABASE_URL": "sqlite:///:memory:",
        "JWT_SECRET": "s",
        "MQTT_HOST": "h",
        "MQTT_USERNAME": "u",
        "MQTT_PASSWORD": "p",
    }.items():
        monkeypatch.setenv(k, v)


def test_missing_required_reports_names(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ConfigError) as exc:
        load_settings(exit_on_error=False)
    assert "DATABASE_URL" in str(exc.value)
    assert "JWT_SECRET" in str(exc.value)


def test_jwt_lifetime_over_cap_rejected(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("JWT_LIFETIME_HOURS", "48")
    with pytest.raises(ConfigError) as exc:
        load_settings(exit_on_error=False)
    assert "exceeds the maximum" in str(exc.value)


def test_jwt_lifetime_at_cap_allowed(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("JWT_LIFETIME_HOURS", "24")
    settings = load_settings(exit_on_error=False)
    assert settings.jwt_lifetime_hours == 24
