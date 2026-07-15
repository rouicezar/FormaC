import { Activity, AlertTriangle, ArrowRight, Bot, Database, FileSearch, MessageSquareText, RefreshCw, Server, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/Layouts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8897";

type DependencyStatus = "ok" | "not_configured" | "not_started";
type Health = { service: DependencyStatus; database: DependencyStatus; scheduler: DependencyStatus; embedding: DependencyStatus; model: DependencyStatus; feishu: DependencyStatus };

const statusText: Record<DependencyStatus, string> = { ok: "运行正常", not_configured: "尚未配置", not_started: "尚未启动" };

export function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadHealth() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/health`);
      if (!response.ok) throw new Error("健康检查请求失败");
      setHealth(await response.json());
    } catch {
      setHealth(null);
      setError("暂时无法连接后端服务，请检查本地服务状态。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadHealth(); }, []);

  const dependencies = [
    ["业务服务", health?.service, Server], ["业务数据库", health?.database, Database],
    ["向量与嵌入", health?.embedding, FileSearch], ["回答模型", health?.model, Bot],
    ["自动扫描", health?.scheduler, RefreshCw], ["飞书接入", health?.feishu, MessageSquareText],
  ] as const;
  const okCount = dependencies.filter(([, status]) => status === "ok").length;

  return (
    <main className="page-content dashboard-page">
      <PageHeader eyebrow="管理端" title="管理首页" description="查看知识库服务状态，以及查询、问答与用户使用概况。" actions={<button className="secondary-button" onClick={loadHealth} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""} />刷新状态</button>} />

      {error && <div className="dashboard-alert" role="alert"><AlertTriangle size={18} /><span>{error}</span></div>}

      <section className="metric-grid" aria-label="核心指标">
        <article className="metric-card"><div className="metric-heading"><span>原文查询次数</span><FileSearch size={18} /></div><strong>—</strong><p>统计接口待接入</p></article>
        <article className="metric-card"><div className="metric-heading"><span>知识问答次数</span><MessageSquareText size={18} /></div><strong>—</strong><p>统计接口待接入</p></article>
        <article className="metric-card"><div className="metric-heading"><span>已绑定用户</span><Users size={18} /></div><strong>—</strong><p>用户服务待接入</p></article>
        <article className="metric-card featured"><div className="metric-heading"><span>运行正常的服务</span><Activity size={18} /></div><strong>{loading ? "…" : `${okCount}/${dependencies.length}`}</strong><p>来自实时健康检查</p></article>
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-panel health-panel">
          <div className="section-heading"><div><h2>系统连接状态</h2><p>数据来自当前 FastAPI `/health` 接口</p></div><span className={`connection-pill ${error ? "error" : ""}`}>{error ? "连接异常" : loading ? "正在检查" : "检查完成"}</span></div>
          <div className="dependency-list">{dependencies.map(([name, status, Icon]) => <div className="dependency-row" key={name}><div><span className="dependency-icon"><Icon size={17} /></span><strong>{name}</strong></div><span className={`dependency-status ${status || "loading"}`}><i />{status ? statusText[status] : "检查中"}</span></div>)}</div>
        </article>
        <aside className="dashboard-side">
          <article className="dashboard-panel"><div className="section-heading"><div><h2>快捷管理</h2><p>进入已经具备真实能力的管理页面</p></div></div><Link className="admin-quick-link" to="/admin/knowledge"><Database size={18} /><span><strong>知识库与扫描</strong><small>管理本地目录与增量扫描</small></span><ArrowRight size={17} /></Link><Link className="admin-quick-link" to="/admin/retrieval-lab"><FileSearch size={18} /><span><strong>检索实验室</strong><small>核验权限、模型与引用链路</small></span><ArrowRight size={17} /></Link></article>
          <article className="privacy-note"><span><Bot size={18} /></span><div><strong>敏感云端策略默认关闭</strong><p>任何敏感片段发送给云端前，都必须经过服务端隐私策略校验。</p></div></article>
        </aside>
      </section>
    </main>
  );
}
