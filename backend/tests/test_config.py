"""Secret-safe dotenv regression tests; never read the developer's .env."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.schemas.chat import ChatResult
from app.schemas.common import Meta
from tests.factories import UID


def test_default_dotenv_path_is_anchored_to_backend():
    from app import config

    expected = Path(config.__file__).resolve().parents[1] / ".env"
    assert Settings.model_config["env_file"] == expected
    assert expected.is_absolute()


@pytest.fixture
def isolated_dotenv(tmp_path, monkeypatch):
    # Avoid process environment values overriding the isolated test file.
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
        monkeypatch.delenv(field, raising=False)
    backend = tmp_path / "backend"
    backend.mkdir()
    env_file = backend / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=fake-config-regression-key\n"
        "INTELLIGENCE_MODE=auto\n"
        "AS_OF_DATE=2026-11-07\n"
        f"DEMO_USER_ID={UID}\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)
    unrelated = tmp_path / "unrelated-working-directory"
    unrelated.mkdir()
    # A same-named file in the launch directory must not override backend/.env.
    (unrelated / ".env").write_text("GEMINI_API_KEY=wrong-launch-directory-key\n", encoding="utf-8")
    monkeypatch.chdir(unrelated)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_key_loads_outside_backend_directory(isolated_dotenv):
    settings = get_settings()
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "fake-config-regression-key"
    assert "fake-config-regression-key" not in repr(settings)


def test_explicit_dotenv_disable_still_works(isolated_dotenv):
    assert Settings(_env_file=None).gemini_api_key is None


def test_chat_receives_same_dotenv_settings_object(isolated_dotenv, repo, monkeypatch):
    from intelligence import copilot

    settings = get_settings()
    received = []

    def fake_chat(messages, tools):
        received.append(tools.settings)
        assert tools.settings.gemini_api_key is not None
        return ChatResult(
            reply="Configuration detected.", tool_calls=[],
            meta=Meta(source="model", as_of=tools.profile.as_of,
                      generated_at=datetime.now(timezone.utc)),
        )

    monkeypatch.setattr(copilot, "chat", fake_chat)
    client = TestClient(create_app(repo=repo))
    result = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hello"}]})
    assert result.status_code == 200
    assert result.json()["meta"]["source"] == "model"
    assert received == [settings]
    assert received[0] is settings
