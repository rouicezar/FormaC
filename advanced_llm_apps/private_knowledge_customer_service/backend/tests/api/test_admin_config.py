from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.configuration import ConfigurationStore
from app.main import create_app
from app.domain.models import AuditEvent


def make_store(tmp_path: Path) -> ConfigurationStore:
    return ConfigurationStore(
        tmp_path / "config.json",
        Settings(
            knowledge_root="/data/knowledge",
            deepseek_api_key="initial-secret",
            deepseek_model="deepseek-v4-flash",
            ollama_model="qwen3:0.6b",
            ollama_host="http://localhost:11434",
        ),
    )


def test_admin_config_hides_secrets_and_exposes_fixed_partition_paths(tmp_path: Path) -> None:
    client = TestClient(create_app(configuration_store=make_store(tmp_path)))

    response = client.get("/admin/config")

    assert response.status_code == 200
    assert response.json()["knowledge"] == {
        "root": "/data/knowledge",
        "public_path": "/data/knowledge/public",
        "sensitive_path": "/data/knowledge/sensitive",
    }
    assert response.json()["models"]["deepseek"]["api_key_configured"] is True
    assert "initial-secret" not in response.text


def test_admin_config_saves_non_secret_settings_and_write_only_key(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    knowledge_root = tmp_path / "company-knowledge"
    (knowledge_root / "public").mkdir(parents=True)
    (knowledge_root / "sensitive").mkdir()
    store = make_store(tmp_path)
    client = TestClient(create_app(configuration_store=store))

    response = client.put(
        "/admin/config",
        json={
            "knowledge_root": str(knowledge_root),
            "active_provider": "ollama",
            "deepseek_model": "deepseek-reasoner",
            "deepseek_api_key": "replacement-secret",
            "ollama_model": "qwen3:8b",
            "ollama_host": "http://ollama.internal:11434",
            "allow_sensitive_cloud": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["models"]["active_provider"] == "ollama"
    assert response.json()["knowledge"]["public_path"] == str(knowledge_root / "public")
    assert "replacement-secret" not in response.text
    assert path.stat().st_mode & 0o777 == 0o600

    reloaded = ConfigurationStore(path, Settings()).snapshot()
    assert reloaded.deepseek_api_key == "replacement-secret"
    assert reloaded.allow_sensitive_cloud is False


def test_sensitive_cloud_enable_requires_explicit_confirmation(tmp_path: Path) -> None:
    client = TestClient(create_app(configuration_store=make_store(tmp_path)))

    rejected = client.put(
        "/admin/config",
        json={"allow_sensitive_cloud": True, "confirm_sensitive_cloud": False},
    )
    accepted = client.put(
        "/admin/config",
        json={"allow_sensitive_cloud": True, "confirm_sensitive_cloud": True},
    )

    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "开启敏感内容云端发送前必须二次确认"
    assert accepted.status_code == 200
    assert accepted.json()["models"]["allow_sensitive_cloud"] is True


def test_unknown_provider_is_rejected(tmp_path: Path) -> None:
    client = TestClient(create_app(configuration_store=make_store(tmp_path)))

    response = client.put("/admin/config", json={"active_provider": "unknown"})

    assert response.status_code == 422


def test_knowledge_root_must_have_fixed_public_and_sensitive_dirs(tmp_path: Path) -> None:
    root = tmp_path / "bad-knowledge"
    root.mkdir()
    client = TestClient(create_app(configuration_store=make_store(tmp_path)))

    missing_public = client.put("/admin/config", json={"knowledge_root": str(root)})
    (root / "public").mkdir()
    missing_sensitive = client.put("/admin/config", json={"knowledge_root": str(root)})

    assert missing_public.status_code == 400
    assert missing_public.json()["detail"] == "知识库根目录必须包含 public/ 子目录"
    assert missing_sensitive.status_code == 400
    assert missing_sensitive.json()["detail"] == "知识库根目录必须包含 sensitive/ 子目录"


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1


class FakeRuntime:
    def __init__(self, session: FakeSession) -> None:
        self.session = session


def test_sensitive_policy_change_is_audited(tmp_path: Path) -> None:
    app = create_app(configuration_store=make_store(tmp_path))
    session = FakeSession()
    app.state.runtime = FakeRuntime(session)
    client = TestClient(app)

    response = client.put(
        "/admin/config",
        json={"allow_sensitive_cloud": True, "confirm_sensitive_cloud": True},
    )

    assert response.status_code == 200
    assert response.json()["audit_recorded"] is True
    assert session.commits == 1
    event = session.added[0]
    assert isinstance(event, AuditEvent)
    assert event.action == "update_sensitive_cloud_policy"
    assert event.details == {"before": False, "after": True}
