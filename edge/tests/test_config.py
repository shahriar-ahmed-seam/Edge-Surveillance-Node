import pytest

from src.config import ConfigError, load_config


REQUIRED = {
    "NODE_ID": "node-test",
    "MODEL_PATH": "/tmp/model.onnx",
    "MQTT_HOST": "localhost",
    "MQTT_USERNAME": "edge",
    "MQTT_PASSWORD": "secret",
}


def _set_env(monkeypatch, overrides=None, remove=None):
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)
    for k, v in (overrides or {}).items():
        monkeypatch.setenv(k, v)
    for k in remove or []:
        monkeypatch.delenv(k, raising=False)


def test_loads_with_required_and_defaults(monkeypatch):
    _set_env(monkeypatch)
    cfg = load_config(exit_on_error=False)
    assert cfg.node_id == "node-test"
    assert cfg.target_fps == 12.0  # default
    assert cfg.topic_events() == "nodes/node-test/events"


def test_missing_required_fails_fast_with_names(monkeypatch):
    _set_env(monkeypatch, remove=["MQTT_HOST", "NODE_ID"])
    with pytest.raises(ConfigError) as exc:
        load_config(exit_on_error=False)
    assert "MQTT_HOST" in str(exc.value)
    assert "NODE_ID" in str(exc.value)


def test_exit_on_error_calls_sys_exit(monkeypatch):
    _set_env(monkeypatch, remove=["MODEL_PATH"])
    with pytest.raises(SystemExit) as exc:
        load_config(exit_on_error=True)
    assert exc.value.code == 1


def test_invalid_cast_raises(monkeypatch):
    _set_env(monkeypatch, overrides={"TARGET_FPS": "not-a-number"})
    with pytest.raises(ConfigError):
        load_config(exit_on_error=False)
