import { Cloud, Cpu, KeyRound, Loader2, LockKeyhole, Save, ShieldAlert } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { getAdminConfig, saveAdminConfig, type AdminConfig, type Provider } from "../api";
import { PageHeader } from "../components/Layouts";

export function ModelsPage() {
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [provider, setProvider] = useState<Provider>("ollama");
  const [deepseekModel, setDeepseekModel] = useState(""); const [apiKey, setApiKey] = useState("");
  const [ollamaModel, setOllamaModel] = useState(""); const [ollamaHost, setOllamaHost] = useState("");
  const [allowSensitive, setAllowSensitive] = useState(false); const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(true); const [error, setError] = useState(""); const [message, setMessage] = useState("");

  function hydrate(data: AdminConfig) { setConfig(data); setProvider(data.models.active_provider); setDeepseekModel(data.models.deepseek.model); setOllamaModel(data.models.ollama.model); setOllamaHost(data.models.ollama.endpoint); setAllowSensitive(data.models.allow_sensitive_cloud); }
  useEffect(() => { void getAdminConfig().then(hydrate).catch((caught) => setError(caught instanceof Error ? caught.message : "配置读取失败。" )).finally(() => setBusy(false)); }, []);
  async function persist(confirmSensitiveCloud = false) { setBusy(true); setError(""); setMessage(""); try { const data = await saveAdminConfig({ active_provider: provider, deepseek_model: deepseekModel, ...(apiKey ? { deepseek_api_key: apiKey } : {}), ollama_model: ollamaModel, ollama_host: ollamaHost, allow_sensitive_cloud: allowSensitive, confirm_sensitive_cloud: confirmSensitiveCloud }); hydrate(data); setApiKey(""); setConfirmOpen(false); setMessage(data.audit_recorded ? "模型与隐私配置已保存、立即应用并写入审计。" : "模型与隐私配置已保存并立即应用。" ); } catch (caught) { setError(caught instanceof Error ? caught.message : "配置保存失败。" ); } finally { setBusy(false); } }
  function save(event: FormEvent) { event.preventDefault(); if (allowSensitive && !config?.models.allow_sensitive_cloud) { setConfirmOpen(true); return; } void persist(); }

  return <main className="page-content admin-config-page"><PageHeader eyebrow="模型插件与隐私" title="模型配置" description="管理 DeepSeek 云端与 Ollama 本地插件。原文查询不经过任何模型。" />
    {error && <div className="config-alert error" role="alert">{error}</div>}{message && <div className="config-alert success" role="status">{message}</div>}
    {busy && !config ? <div className="config-loading"><Loader2 className="spin" />正在读取配置</div> : <form onSubmit={save} className="admin-config-grid model-grid">
      <section className={`config-card provider-card ${provider === "deepseek" ? "selected" : ""}`}><div className="config-card-title"><Cloud /><div><h2>DeepSeek 云端模型</h2><p>OpenAI 兼容云端插件</p></div></div><label>模型名称<input value={deepseekModel} onChange={(event) => setDeepseekModel(event.target.value)} /></label><label>API Key（仅写入本机秘密配置）<input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={config?.models.deepseek.api_key_configured ? "已配置，留空表示不修改" : "尚未配置"} /></label><button type="button" className="provider-select" onClick={() => setProvider("deepseek")}><KeyRound size={15} />{provider === "deepseek" ? "当前回答模型" : "设为回答模型"}</button></section>
      <section className={`config-card provider-card ${provider === "ollama" ? "selected" : ""}`}><div className="config-card-title"><Cpu /><div><h2>Ollama 本地模型</h2><p>敏感知识可在本地完成总结</p></div></div><label>服务地址<input value={ollamaHost} onChange={(event) => setOllamaHost(event.target.value)} /></label><label>模型名称<input value={ollamaModel} onChange={(event) => setOllamaModel(event.target.value)} /></label><button type="button" className="provider-select" onClick={() => setProvider("ollama")}><KeyRound size={15} />{provider === "ollama" ? "当前回答模型" : "设为回答模型"}</button></section>
      <section className="config-card full privacy-card"><div className="config-card-title"><LockKeyhole /><div><h2>敏感云端策略</h2><p>关闭时，敏感证据不会进入云端模型请求，只返回本地原文。</p></div></div><label className="policy-switch"><span><strong>允许敏感内容发送给云端模型</strong><small>高风险设置，默认关闭；开启必须二次确认。</small></span><input type="checkbox" checked={allowSensitive} onChange={(event) => setAllowSensitive(event.target.checked)} /></label></section>
      <div className="config-submit full"><button className="primary-action" disabled={busy}><Save size={17} />{busy ? "正在保存" : "保存更改"}</button></div>
    </form>}
    {confirmOpen && <div className="confirm-backdrop" role="presentation"><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="sensitive-confirm-title"><ShieldAlert /><h2 id="sensitive-confirm-title">确认开启敏感内容云端发送？</h2><p>开启后，内部用户问答命中的敏感原文可能发送到当前云端模型。该策略会立即生效。</p><div><button className="secondary-button" onClick={() => { setConfirmOpen(false); setAllowSensitive(false); }}>取消</button><button className="danger-action" onClick={() => void persist(true)}>确认开启</button></div></section></div>}
  </main>;
}
