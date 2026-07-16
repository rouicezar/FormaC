import hmac
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from app.channels.feishu.events import (
    FeishuChannelService,
    FeishuReplyClient,
    decrypt_payload,
    verify_signature,
)
from app.configuration import ConfigurationStore


router = APIRouter(tags=["飞书通道"])


class FeishuConfigurationResponse(BaseModel):
    app_id: str | None
    app_secret_configured: bool
    verification_token_configured: bool
    encrypt_key_configured: bool
    callback_path: str = "/feishu/events"
    protocol: tuple[str, ...] = ("查询：", "问答：", "历史", "帮助")


class FeishuConfigurationUpdate(BaseModel):
    app_id: str | None = None
    app_secret: str | None = None
    verification_token: str | None = None
    encrypt_key: str | None = None


def _store(request: Request) -> ConfigurationStore:
    store = request.app.state.configuration_store
    if store is None:
        raise HTTPException(status_code=503, detail="配置服务尚未启用")
    return store


def _response(settings) -> FeishuConfigurationResponse:
    return FeishuConfigurationResponse(
        app_id=settings.feishu_app_id,
        app_secret_configured=bool(settings.feishu_app_secret),
        verification_token_configured=bool(settings.feishu_verification_token),
        encrypt_key_configured=bool(settings.feishu_encrypt_key),
    )


@router.get("/admin/feishu/config", response_model=FeishuConfigurationResponse)
def read_feishu_configuration(request: Request) -> FeishuConfigurationResponse:
    return _response(_store(request).snapshot())


@router.put("/admin/feishu/config", response_model=FeishuConfigurationResponse)
def save_feishu_configuration(
    payload: FeishuConfigurationUpdate, request: Request
) -> FeishuConfigurationResponse:
    changes = {
        "feishu_app_id": payload.app_id,
        "feishu_app_secret": payload.app_secret,
        "feishu_verification_token": payload.verification_token,
        "feishu_encrypt_key": payload.encrypt_key,
    }
    settings = _store(request).update(
        {key: value for key, value in changes.items() if value is not None}
    )
    if settings.feishu_app_id and settings.feishu_app_secret:
        request.app.state.feishu_reply_client = FeishuReplyClient(
            settings.feishu_app_id, settings.feishu_app_secret
        )
    return _response(settings)


@router.post("/feishu/events")
async def receive_feishu_event(
    request: Request, background_tasks: BackgroundTasks
) -> dict[str, object]:
    settings = _store(request).snapshot()
    service: FeishuChannelService | None = request.app.state.feishu_service
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="飞书回调不是有效 JSON") from error

    encrypted_text = payload.get("encrypt")
    if isinstance(encrypted_text, str):
        if not settings.feishu_encrypt_key:
            raise HTTPException(status_code=503, detail="飞书 Encrypt Key 尚未配置")
        timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        signature = request.headers.get("X-Lark-Signature", "")
        if not verify_signature(body, timestamp, nonce, settings.feishu_encrypt_key, signature):
            raise HTTPException(status_code=401, detail="飞书回调签名无效")
        try:
            payload = decrypt_payload(encrypted_text, settings.feishu_encrypt_key)
        except Exception as error:
            raise HTTPException(status_code=400, detail="飞书加密回调解密失败") from error

    header = payload.get("header", {})
    token = payload.get("token") or header.get("token")
    if not settings.feishu_verification_token:
        raise HTTPException(status_code=503, detail="飞书 Verification Token 尚未配置")
    if not isinstance(token, str) or not hmac.compare_digest(token, settings.feishu_verification_token):
        raise HTTPException(status_code=401, detail="飞书回调令牌无效")
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    if not settings.feishu_encrypt_key or service is None:
        raise HTTPException(status_code=503, detail="飞书通道尚未配置")

    if not isinstance(encrypted_text, str):
        timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        signature = request.headers.get("X-Lark-Signature", "")
        if not verify_signature(body, timestamp, nonce, settings.feishu_encrypt_key, signature):
            raise HTTPException(status_code=401, detail="飞书回调签名无效")

    if header.get("event_type") != "im.message.receive_v1":
        return {"ok": True, "ignored": True}

    event = payload.get("event", {})
    message = event.get("message", {})
    if message.get("chat_type") != "p2p" and not message.get("mentions"):
        return {"ok": True, "ignored": True}
    try:
        content = json.loads(message.get("content", "{}"))
    except json.JSONDecodeError:
        return {"ok": True, "ignored": True}
    text = content.get("text")
    event_id = header.get("event_id")
    sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id")
    if not all(isinstance(value, str) and value for value in (text, event_id, sender_id)):
        return {"ok": True, "ignored": True}
    reply, duplicate = service.handle(event_id, sender_id, text)
    reply_client = request.app.state.feishu_reply_client
    message_id = message.get("message_id")
    if reply_client is not None and isinstance(message_id, str) and message_id and not duplicate:
        background_tasks.add_task(reply_client.reply_text, message_id, reply)
    return {"ok": True, "reply": reply, "duplicate": duplicate}
