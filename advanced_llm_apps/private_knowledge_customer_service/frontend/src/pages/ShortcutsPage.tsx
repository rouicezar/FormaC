import { ArrowRight, FileSearch, Loader2, MessageSquareText, RefreshCw, ShieldCheck, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getPersonalRecords, type InteractionRecord, type PersonalRecordList } from "../api";
import { PageHeader } from "../components/Layouts";
import { identityLabels, useIdentity } from "../identity";

const kindText = { search: "原文查询", ask: "知识问答" };
const targetPath = { search: "/app/search", ask: "/app/chat" };

type Shortcut = {
  key: string;
  query: string;
  kind: "search" | "ask";
  count: number;
  citations: number;
  lastUsed: string;
};

function buildShortcuts(records: InteractionRecord[]): Shortcut[] {
  const grouped = new Map<string, Shortcut>();
  for (const record of records) {
    const normalizedQuery = record.query.trim();
    if (!normalizedQuery) continue;
    const kind = record.kind;
    const key = `${kind}:${normalizedQuery.toLocaleLowerCase("zh-CN")}`;
    const existing = grouped.get(key);
    if (existing) {
      existing.count += 1;
      existing.citations += record.citations.length;
      if (new Date(record.created_at).getTime() > new Date(existing.lastUsed).getTime()) {
        existing.lastUsed = record.created_at;
      }
      continue;
    }
    grouped.set(key, {
      key,
      query: normalizedQuery,
      kind,
      count: 1,
      citations: record.citations.length,
      lastUsed: record.created_at,
    });
  }
  return Array.from(grouped.values())
    .sort((left, right) => right.count - left.count || new Date(right.lastUsed).getTime() - new Date(left.lastUsed).getTime())
    .slice(0, 8);
}

function ShortcutCard({ shortcut }: { shortcut: Shortcut }) {
  const href = `${targetPath[shortcut.kind]}?q=${encodeURIComponent(shortcut.query)}`;
  return <Link className="shortcut-card" to={href}>
    <span className="shortcut-icon">{shortcut.kind === "search" ? <FileSearch size={18} /> : <MessageSquareText size={18} />}</span>
    <div>
      <strong>{shortcut.query}</strong>
      <p>{kindText[shortcut.kind]} · 使用 {shortcut.count} 次 · 引用 {shortcut.citations} 条</p>
    </div>
    <ArrowRight size={17} />
  </Link>;
}

export function ShortcutsPage() {
  const identity = useIdentity();
  const [data, setData] = useState<PersonalRecordList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getPersonalRecords(identity.requesterId, {
        feishuUserId: identity.feishuUserId,
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "快捷入口读取失败。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [identity.requesterId, identity.feishuUserId]);

  const shortcuts = useMemo(() => buildShortcuts(data?.records || []), [data]);
  const recent = data?.records.slice(0, 3) || [];

  return <main className="page-content shortcuts-page">
    <PageHeader
      eyebrow="个人高频入口"
      title="快捷入口"
      description="根据当前身份的网页与飞书历史生成，不展示全局热门问题。"
      actions={<button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""} />刷新</button>}
    />
    <section className="history-identity-card">
      <ShieldCheck size={20} />
      <div>
        <strong>{identityLabels[identity.kind]} · {identity.displayName}</strong>
        <p>当前快捷入口来自 <code>{identity.requesterId}</code>{identity.feishuUserId ? <> 和 <code>{identity.feishuUserId}</code></> : null} 的个人记录。</p>
      </div>
      <span>可访问：{identity.visibleScope}</span>
    </section>
    {error && <div className="config-alert error" role="alert">{error}</div>}
    {loading && !data ? <div className="config-loading"><Loader2 className="spin" />正在生成个人快捷入口</div> : !shortcuts.length ? <section className="shortcut-empty">
      <Zap size={34} />
      <h2>还没有可生成的快捷入口</h2>
      <p>完成几次原文查询或知识问答后，这里会自动汇总你的高频问题。飞书绑定后，也会合并同一飞书身份的历史。</p>
      <div>
        <Link to="/app/search">去查询原文<ArrowRight size={15} /></Link>
        <Link to="/app/chat">去知识问答<ArrowRight size={15} /></Link>
      </div>
    </section> : <div className="shortcut-layout">
      <section className="shortcut-panel">
        <div className="section-heading">
          <div><h2>高频入口</h2><p>按个人使用次数排序；点击后会带入原查询词。</p></div>
          <span className="connection-pill ok">{shortcuts.length} 个</span>
        </div>
        <div className="shortcut-grid">{shortcuts.map((shortcut) => <ShortcutCard key={shortcut.key} shortcut={shortcut} />)}</div>
      </section>
      <aside className="shortcut-panel">
        <div className="section-heading">
          <div><h2>最近使用</h2><p>只显示当前身份的最新记录。</p></div>
        </div>
        <div className="recent-shortcut-list">{recent.map((record) => <Link key={record.id} to={`${targetPath[record.kind]}?q=${encodeURIComponent(record.query)}`}>
          <strong>{record.query}</strong>
          <span>{kindText[record.kind]} · {new Date(record.created_at).toLocaleString("zh-CN")}</span>
        </Link>)}</div>
      </aside>
    </div>}
  </main>;
}
