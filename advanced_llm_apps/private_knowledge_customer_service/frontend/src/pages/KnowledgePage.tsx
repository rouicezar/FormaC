import { Database, FileLock2, FileText, FolderOpen, Loader2, RefreshCw, Save, ShieldCheck } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { getAdminConfig, saveAdminConfig, startManualScan, type AdminConfig, type ScanReport } from "../api";
import { PageHeader } from "../components/Layouts";

export function KnowledgePage() {
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [root, setRoot] = useState("");
  const [scan, setScan] = useState<ScanReport | null>(null);
  const [busy, setBusy] = useState<"loading" | "saving" | "scanning" | "">("loading");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { void getAdminConfig().then((data) => { setConfig(data); setRoot(data.knowledge.root || ""); setError(""); }).catch((caught) => setError(caught instanceof Error ? caught.message : "配置读取失败。" )).finally(() => setBusy("")); }, []);

  async function save(event: FormEvent) {
    event.preventDefault(); setBusy("saving"); setError(""); setMessage("");
    try { const data = await saveAdminConfig({ knowledge_root: root.trim() || null }); setConfig(data); setRoot(data.knowledge.root || ""); setMessage("知识目录配置已保存并立即应用。下一次扫描将读取该目录。"); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "配置保存失败。" ); }
    finally { setBusy(""); }
  }

  async function scanNow() {
    setBusy("scanning"); setError(""); setMessage("");
    try { const result = await startManualScan(); setScan(result); setMessage(result.failed ? "扫描已完成，但存在处理失败的文件。" : "增量扫描完成，索引已同步。" ); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "扫描失败。" ); }
    finally { setBusy(""); }
  }

  return <main className="page-content admin-config-page">
    <PageHeader eyebrow="本地知识源" title="知识库管理" description="配置唯一授权根目录，并复用现有增量扫描、解析和分区索引能力。" actions={<button className="primary-action" onClick={scanNow} disabled={!!busy || !config?.knowledge.root}>{busy === "scanning" ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}{busy === "scanning" ? "正在扫描" : "立即扫描"}</button>} />
    {error && <div className="config-alert error" role="alert">{error}</div>}{message && <div className="config-alert success" role="status">{message}</div>}
    {busy === "loading" ? <div className="config-loading"><Loader2 className="spin" />正在读取配置</div> : <div className="admin-config-grid">
      <form className="config-card wide" onSubmit={save}><div className="config-card-title"><FolderOpen /><div><h2>路径配置</h2><p>系统只读取固定的 public/ 与 sensitive/ 子目录，不上传、移动或修改源文件。</p></div></div><label>知识库根目录<input value={root} onChange={(event) => setRoot(event.target.value)} placeholder="例如：/Users/name/Knowledge" /></label><div className="partition-paths"><div><FileText /><span>公开知识</span><strong>{root ? `${root.replace(/\/$/, "")}/public` : "等待配置根目录"}</strong></div><div><FileLock2 /><span>敏感知识</span><strong>{root ? `${root.replace(/\/$/, "")}/sensitive` : "等待配置根目录"}</strong></div></div><button className="secondary-button" disabled={!!busy}><Save size={16} />{busy === "saving" ? "正在保存" : "保存路径配置"}</button></form>
      <section className="config-card"><div className="config-card-title"><ShieldCheck /><div><h2>安全边界</h2><p>服务端按身份决定可检索分区。</p></div></div><ul className="policy-list"><li>外部与匿名身份仅进入公开索引</li><li>敏感目录仅内部身份可检索</li><li>新索引失败时保留旧索引</li><li>单个文件失败不终止整批扫描</li></ul></section>
      <section className="config-card full"><div className="config-card-title"><Database /><div><h2>最近手动扫描</h2><p>本页只展示当前会话触发的真实扫描结果。</p></div></div>{!scan ? <div className="inline-empty">尚未从本页发起扫描。</div> : <div className="scan-metrics">{[["新增", scan.added], ["更新", scan.updated], ["删除", scan.deleted], ["跳过", scan.skipped], ["失败", scan.failed]].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>}{scan?.errors.length ? <div className="scan-errors">{scan.errors.map((item, index) => <p key={index}><strong>{item.path}</strong>{item.error}</p>)}</div> : null}</section>
    </div>}
  </main>;
}
