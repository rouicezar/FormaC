import hashlib
import hmac
import json
from urllib.request import Request, urlopen
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.domain.models import FeishuEvent
from app.permissions.identities import IdentityRole, IdentityService
from app.retrieval.raglite_adapter import IdentityKind


class FeishuReplyClient:
    """Minimal Feishu Open API client for asynchronous plain-text replies."""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret

    @staticmethod
    def _post(url: str, payload: dict, *, token: str | None = None) -> dict:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed Feishu host
            return json.loads(response.read())

    def reply_text(self, message_id: str, text: str) -> None:
        token_response = self._post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            {"app_id": self.app_id, "app_secret": self.app_secret},
        )
        token = token_response.get("tenant_access_token")
        if not token:
            raise RuntimeError("飞书租户访问令牌获取失败")
        response = self._post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            {"msg_type": "text", "content": json.dumps({"text": text}, ensure_ascii=False)},
            token=token,
        )
        if response.get("code") != 0:
            raise RuntimeError(f"飞书消息回复失败：{response.get('msg', 'unknown error')}")


class FeishuCommand(StrEnum):
    SEARCH = "search"
    ASK = "ask"
    HISTORY = "history"
    HELP = "help"


def parse_command(text: str) -> tuple[FeishuCommand, str]:
    value = text.strip()
    if value == "历史": return FeishuCommand.HISTORY, ""
    if value == "帮助": return FeishuCommand.HELP, ""
    for prefix, command in (("查询：", FeishuCommand.SEARCH), ("查询:", FeishuCommand.SEARCH), ("问答：", FeishuCommand.ASK), ("问答:", FeishuCommand.ASK)):
        if value.startswith(prefix): return command, value[len(prefix):].strip()
    return FeishuCommand.ASK, value


def verify_signature(body: bytes, timestamp: str, nonce: str, encrypt_key: str, signature: str) -> bool:
    digest = hashlib.sha256(timestamp.encode() + nonce.encode() + encrypt_key.encode() + body).hexdigest()
    return hmac.compare_digest(digest, signature)


@dataclass(frozen=True, slots=True)
class StoredFeishuEvent:
    id: UUID; event_id: str; sender_id: str; command: str; request_text: str; response_text: str; created_at: datetime


class InMemoryFeishuEventRepository:
    def __init__(self) -> None: self.events: dict[str, StoredFeishuEvent] = {}
    def get(self, event_id: str): return self.events.get(event_id)
    def record(self, event_id, sender_id, command, request_text, response_text):
        if event_id in self.events: return self.events[event_id]
        item = StoredFeishuEvent(uuid4(), event_id, sender_id, command, request_text, response_text, datetime.now(UTC)); self.events[event_id] = item; return item
    def history(self, sender_id, limit=5): return [item for item in reversed(list(self.events.values())) if item.sender_id == sender_id][:limit]


class SqlAlchemyFeishuEventRepository:
    def __init__(self, engine: Engine) -> None: self.factory = sessionmaker(bind=engine, expire_on_commit=False)
    @staticmethod
    def _item(row): return StoredFeishuEvent(row.id, row.event_id, row.sender_id, row.command, row.request_text, row.response_text, row.created_at)
    def get(self, event_id: str):
        with self.factory() as session:
            row = session.scalar(select(FeishuEvent).where(FeishuEvent.event_id == event_id)); return self._item(row) if row else None
    def record(self, event_id, sender_id, command, request_text, response_text):
        existing = self.get(event_id)
        if existing: return existing
        with self.factory() as session:
            row = FeishuEvent(event_id=event_id, sender_id=sender_id, command=command, request_text=request_text, response_text=response_text); session.add(row)
            try: session.commit(); return self._item(row)
            except IntegrityError: session.rollback(); return self.get(event_id)
    def history(self, sender_id, limit=5):
        with self.factory() as session:
            rows = session.scalars(select(FeishuEvent).where(FeishuEvent.sender_id == sender_id).order_by(FeishuEvent.created_at.desc()).limit(limit)).all(); return [self._item(row) for row in rows]


class FeishuChannelService:
    def __init__(self, *, repository, identities: IdentityService, search_service, ask_service) -> None:
        self.repository, self.identities, self.search_service, self.ask_service = repository, identities, search_service, ask_service
    def handle(self, event_id: str, sender_id: str, text: str) -> tuple[str, bool]:
        existing = self.repository.get(event_id)
        if existing: return existing.response_text, True
        command, query = parse_command(text)
        role = self.identities.resolve_feishu_role(sender_id)
        identity = IdentityKind.INTERNAL if role is IdentityRole.INTERNAL else IdentityKind.EXTERNAL
        if command is FeishuCommand.HELP:
            reply = "CoreKnowledge 纯文本助手\n查询：问题 — 返回原文\n问答：问题 — 基于证据回答\n历史 — 最近记录\n帮助 — 查看本说明"
        elif command is FeishuCommand.HISTORY:
            items = self.repository.history(sender_id)
            reply = "最近记录：\n" + "\n".join(f"- {item.request_text}" for item in items) if items else "暂无历史记录。"
        elif not query: reply = "请输入需要查询或问答的内容。"
        elif command is FeishuCommand.SEARCH:
            result = self.search_service.search(query, identity=identity, limit=5)
            reply = "未检索到相关原文。" if not result.results else "原文查询：\n" + "\n".join(f"[{i}] {item.evidence}\n来源：{item.source}" for i, item in enumerate(result.results, 1))
        else:
            answer = self.ask_service.ask(query, identity=identity, provider_name="ollama", allow_sensitive_cloud=False)
            citations = "\n".join(f"[{i}] {item.source}" for i, item in enumerate(answer.citations, 1))
            reply = answer.text + (f"\n\n引用：\n{citations}" if citations else "")
        self.repository.record(event_id, sender_id, command.value, text, reply)
        return reply, False
