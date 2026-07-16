import hashlib
import json

from app.channels.feishu.events import (
    FeishuCommand,
    InMemoryFeishuEventRepository,
    parse_command,
    verify_signature,
)


def test_plain_text_protocol() -> None:
    assert parse_command("查询：退款期限") == (FeishuCommand.SEARCH, "退款期限")
    assert parse_command("问答：退款期限") == (FeishuCommand.ASK, "退款期限")
    assert parse_command("历史") == (FeishuCommand.HISTORY, "")
    assert parse_command("帮助") == (FeishuCommand.HELP, "")
    assert parse_command("退款期限") == (FeishuCommand.ASK, "退款期限")


def test_signature_uses_timestamp_nonce_encrypt_key_and_raw_body() -> None:
    body = b'{"event":"message"}'
    expected = hashlib.sha256(b"1700000000nonceencrypt" + body).hexdigest()
    assert verify_signature(body, "1700000000", "nonce", "encrypt", expected)
    assert not verify_signature(body, "1700000001", "nonce", "encrypt", expected)


def test_event_repository_is_idempotent_and_keeps_history() -> None:
    repository = InMemoryFeishuEventRepository()
    first = repository.record("evt-1", "ou-1", "ask", "问题", "回答")
    duplicate = repository.record("evt-1", "ou-1", "ask", "问题", "新回答")
    assert first is duplicate
    assert repository.history("ou-1") == [first]
