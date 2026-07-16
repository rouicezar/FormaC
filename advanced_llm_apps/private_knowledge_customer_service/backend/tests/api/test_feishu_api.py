import hashlib
import json
from base64 import b64encode
from os import urandom

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from fastapi.testclient import TestClient

from app.channels.feishu.events import FeishuChannelService, InMemoryFeishuEventRepository
from app.config import Settings
from app.configuration import ConfigurationStore
from app.main import create_app
from app.permissions.identities import IdentityService, InMemoryIdentityRepository


class FakeSearch:
    def search(self, query, *, identity, limit=10):
        return type("Response", (), {"results": (), "query": query})()


class FakeAsk:
    def ask(self, question, *, identity, provider_name, allow_sensitive_cloud=False):
        return type("Answer", (), {"text": "知识回答", "citations": (), "mode": "generate"})()


class FakeReplyClient:
    def __init__(self):
        self.replies = []

    def reply_text(self, message_id, text):
        self.replies.append((message_id, text))


def make_app(tmp_path, reply_client=None):
    settings = Settings(
        feishu_app_id="cli_test",
        feishu_app_secret="secret",
        feishu_verification_token="token",
        feishu_encrypt_key="encrypt",
    )
    store = ConfigurationStore(tmp_path / "config.json", settings)
    identities = IdentityService(InMemoryIdentityRepository())
    channel = FeishuChannelService(
        repository=InMemoryFeishuEventRepository(),
        identities=identities,
        search_service=FakeSearch(),
        ask_service=FakeAsk(),
    )
    return create_app(
        configuration_store=store,
        identity_service=identities,
        feishu_service=channel,
        feishu_reply_client=reply_client,
    )


def make_challenge_app(tmp_path):
    settings = Settings(feishu_verification_token="token")
    store = ConfigurationStore(tmp_path / "config.json", settings)
    return create_app(configuration_store=store)


def signed_headers(body: bytes):
    timestamp, nonce = "1700000000", "nonce"
    signature = hashlib.sha256(timestamp.encode() + nonce.encode() + b"encrypt" + body).hexdigest()
    return {"X-Lark-Request-Timestamp": timestamp, "X-Lark-Request-Nonce": nonce, "X-Lark-Signature": signature, "Content-Type": "application/json"}


def encrypt_payload(payload: dict) -> str:
    key = hashlib.sha256(b"encrypt").digest()
    iv = urandom(16)
    padder = PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(json.dumps(payload, ensure_ascii=False).encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return b64encode(iv + encryptor.update(padded) + encryptor.finalize()).decode()


def test_url_verification_challenge(tmp_path) -> None:
    client = TestClient(make_app(tmp_path))
    body = json.dumps({"type": "url_verification", "token": "token", "challenge": "abc"}).encode()
    response = client.post("/feishu/events", content=body, headers=signed_headers(body))
    assert response.status_code == 200
    assert response.json() == {"challenge": "abc"}


def test_url_verification_challenge_does_not_require_encrypt_key(tmp_path) -> None:
    client = TestClient(make_challenge_app(tmp_path))
    response = client.post(
        "/feishu/events",
        json={"type": "url_verification", "token": "token", "challenge": "abc"},
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc"}


def test_message_callback_defaults_unknown_user_to_external_and_deduplicates(tmp_path) -> None:
    reply_client = FakeReplyClient()
    app = make_app(tmp_path, reply_client)
    client = TestClient(app)
    payload = {"schema": "2.0", "header": {"event_id": "evt-1", "token": "token", "event_type": "im.message.receive_v1"}, "event": {"sender": {"sender_id": {"open_id": "ou-new"}}, "message": {"message_id": "om-1", "chat_type": "p2p", "content": json.dumps({"text": "帮助"})}}}
    body = json.dumps(payload, ensure_ascii=False).encode()
    first = client.post("/feishu/events", content=body, headers=signed_headers(body))
    second = client.post("/feishu/events", content=body, headers=signed_headers(body))
    assert first.status_code == 200
    assert first.json()["reply"].startswith("CoreKnowledge 纯文本助手")
    assert second.json()["duplicate"] is True
    assert reply_client.replies == [("om-1", first.json()["reply"])]


def test_encrypted_message_callback_is_decrypted_and_replied(tmp_path) -> None:
    reply_client = FakeReplyClient()
    client = TestClient(make_app(tmp_path, reply_client))
    payload = {
        "schema": "2.0",
        "header": {"event_id": "evt-encrypted", "token": "token", "event_type": "im.message.receive_v1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou-encrypted"}},
            "message": {
                "message_id": "om-encrypted",
                "chat_type": "p2p",
                "content": json.dumps({"text": "帮助"}),
            },
        },
    }
    body = json.dumps({"encrypt": encrypt_payload(payload)}, ensure_ascii=False).encode()

    response = client.post("/feishu/events", content=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert response.json()["reply"].startswith("CoreKnowledge 纯文本助手")
    assert reply_client.replies == [("om-encrypted", response.json()["reply"])]


def test_feishu_admin_config_is_write_only_for_secrets(tmp_path) -> None:
    client = TestClient(make_app(tmp_path))
    response = client.get("/admin/feishu/config")
    assert response.status_code == 200
    assert response.json()["app_id"] == "cli_test"
    assert response.json()["app_secret_configured"] is True
    assert "secret" not in response.json().values()
    assert "token" not in response.json().values()
    assert "encrypt" not in response.json().values()


def test_feishu_admin_config_updates_runtime_reply_client(tmp_path) -> None:
    app = make_app(tmp_path)
    client = TestClient(app)
    response = client.put(
        "/admin/feishu/config",
        json={"app_id": "cli_updated", "app_secret": "new-secret"},
    )
    assert response.status_code == 200
    assert response.json()["app_id"] == "cli_updated"
    assert app.state.feishu_reply_client.app_id == "cli_updated"
