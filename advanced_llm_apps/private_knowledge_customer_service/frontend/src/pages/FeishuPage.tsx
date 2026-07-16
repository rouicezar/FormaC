import { Bot, CheckCircle2, KeyRound, Loader2, MessageSquareText, ShieldCheck } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { API, getFeishuConfig, saveFeishuConfig, type FeishuConfig } from "../api";

const commands = [["查询：问题", "检索原文并返回来源"], ["问答：问题", "基于证据生成回答"], ["历史", "查看本人最近五条记录"], ["帮助", "查看纯文本使用说明"]];

export function FeishuPage() {
  const [config, setConfig] = useState<FeishuConfig | null>(null);
  const [form, setForm] = useState({ app_id: "", app_secret: "", verification_token: "", encrypt_key: "" });
  const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [saving, setSaving] = useState(false);
  useEffect(() => { getFeishuConfig().then((value) => { setConfig(value); setForm((old) => ({ ...old, app_id: value.app_id || "" })); }).catch((e: Error) => setError(e.message)); }, []);
  const ready = useMemo(() => Boolean(config?.app_id && config.app_secret_configured && config.verification_token_configured && config.encrypt_key_configured), [config]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    const payload = Object.fromEntries(Object.entries(form).filter(([, value]) => value.trim()));
    try { const updated = await saveFeishuConfig(payload); setConfig(updated); setForm({ app_id: updated.app_id || "", app_secret: "", verification_token: "", encrypt_key: "" }); setNotice("配置已保存；密钥不会回显。请在飞书开放平台完成回调验证。"); }
    catch (e) { setError(e instanceof Error ? e.message : "保存失败"); } finally { setSaving(false); }
  }
  return <div className="admin-feishu-page">
    <header className="page-header"><div><span className="eyebrow">CHANNEL / FEISHU</span><h1>飞书通道</h1><p>配置经过签名验证的纯文本机器人入口，复用内部身份权限与敏感内容策略。</p></div><span className={`feishu-status ${ready ? "ready" : "pending"}`}>{ready ? <CheckCircle2 size={14} /> : <KeyRound size={14} />}{ready ? "配置完整" : "等待配置"}</span></header>
    {error && <div className="page-error">{error}</div>}{notice && <div className="feishu-notice"><ShieldCheck size={17} />{notice}</div>}
    <div className="feishu-layout"><form className="feishu-config-panel" onSubmit={submit}>
      <div className="section-heading"><div><h2>应用与回调配置</h2><p>所有密钥只写入本机 0600 配置文件，读取接口仅返回是否已配置。</p></div><Bot size={21} /></div>
      {!config && !error ? <div className="users-empty"><Loader2 className="spin" /><p>正在读取配置…</p></div> : <>
        <label>App ID<input value={form.app_id} onChange={(e) => setForm({ ...form, app_id: e.target.value })} placeholder="cli_xxxxxxxxx" autoComplete="off" /></label>
        <label>App Secret<input type="password" value={form.app_secret} onChange={(e) => setForm({ ...form, app_secret: e.target.value })} placeholder={config?.app_secret_configured ? "已配置 · 留空保持不变" : "请输入 App Secret"} autoComplete="new-password" /></label>
        <label>Verification Token<input type="password" value={form.verification_token} onChange={(e) => setForm({ ...form, verification_token: e.target.value })} placeholder={config?.verification_token_configured ? "已配置 · 留空保持不变" : "请输入 Verification Token"} autoComplete="new-password" /></label>
        <label>Encrypt Key<input type="password" value={form.encrypt_key} onChange={(e) => setForm({ ...form, encrypt_key: e.target.value })} placeholder={config?.encrypt_key_configured ? "已配置 · 留空保持不变" : "请输入 Encrypt Key"} autoComplete="new-password" /></label>
        <div className="callback-box"><span>事件订阅回调地址</span><code>{API}{config?.callback_path || "/feishu/events"}</code><small>支持 URL challenge、签名及令牌校验、事件幂等；群聊仅处理 @ 机器人的消息。</small></div>
        <button className="primary-button" disabled={saving}>{saving ? <Loader2 className="spin" size={16} /> : <ShieldCheck size={16} />}{saving ? "保存中" : "保存配置"}</button>
      </>}
    </form><section className="feishu-protocol-panel"><div className="section-heading"><div><h2>纯文本协议</h2><p>首期不使用消息卡片或菜单。</p></div><MessageSquareText size={21} /></div><div className="command-list">{commands.map(([command, help]) => <article key={command}><code>{command}</code><p>{help}</p></article>)}</div><div className="privacy-note"><span><ShieldCheck size={18} /></span><div><strong>权限与隐私继承</strong><p>未绑定用户按外部身份降级，仅访问公开分区；内部身份才可检索敏感分区，敏感内容不会发送云端模型。</p></div></div></section></div>
  </div>;
}
