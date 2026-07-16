import { FileSearch, Loader2, MessageSquareText, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getInteractionRecords, type InteractionRecord, type InteractionRecordList } from "../api";
import { PageHeader } from "../components/Layouts";

const channelText = { web: "网页", feishu: "飞书" };
const kindText = { search: "原文查询", ask: "知识问答" };
const identityText = { external: "外部", internal: "内部" };

function excerpt(value: string | null, fallback: string) {
  const text = (value || fallback).trim();
  return text.length > 96 ? `${text.slice(0, 96)}...` : text;
}

function RecordRow({ record }: { record: InteractionRecord }) {
  return <article className="record-row">
    <div className="record-kind-icon">{record.kind === "search" ? <FileSearch size={17} /> : <MessageSquareText size={17} />}</div>
    <div className="record-main">
      <div className="record-title">
        <strong>{record.query}</strong>
        <span>{channelText[record.channel]} · {kindText[record.kind]}</span>
      </div>
      <p>{record.kind === "ask" ? excerpt(record.answer, "问答未返回正文。") : excerpt(record.citations[0]?.evidence || null, "原文查询未命中。")}</p>
      <div className="record-meta">
        <span>{new Date(record.created_at).toLocaleString("zh-CN")}</span>
        <span>请求方：{record.requester_id}</span>
        <span>身份：{identityText[record.identity]}</span>
        <span>引用：{record.citations.length}</span>
      </div>
    </div>
  </article>;
}

export function RecordsPage() {
  const [data, setData] = useState<InteractionRecordList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [channel, setChannel] = useState("");
  const [kind, setKind] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setData(await getInteractionRecords({ channel, kind })); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "全局记录读取失败。"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [channel, kind]);
  const metrics = useMemo(() => {
    const records = data?.records || [];
    return {
      total: data?.total || 0,
      web: records.filter((item) => item.channel === "web").length,
      feishu: records.filter((item) => item.channel === "feishu").length,
      ask: records.filter((item) => item.kind === "ask").length,
    };
  }, [data]);

  return <main className="page-content admin-records-page">
    <PageHeader eyebrow="记录与统计" title="全局记录" description="统一查看网页与飞书产生的原文查询、知识问答和引用记录。" actions={<button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""} />刷新</button>} />
    {error && <div className="config-alert error" role="alert">{error}</div>}
    <section className="record-metric-grid">
      <article><span>当前记录</span><strong>{metrics.total}</strong></article>
      <article><span>网页来源</span><strong>{metrics.web}</strong></article>
      <article><span>飞书来源</span><strong>{metrics.feishu}</strong></article>
      <article><span>知识问答</span><strong>{metrics.ask}</strong></article>
    </section>
    <section className="records-panel">
      <div className="records-toolbar">
        <div><h2>交互明细</h2><p>查询与问答分开记录；敏感内容仍由服务端权限过滤决定。</p></div>
        <div>
          <select aria-label="按来源筛选" value={channel} onChange={(event) => setChannel(event.target.value)}>
            <option value="">全部来源</option><option value="web">网页</option><option value="feishu">飞书</option>
          </select>
          <select aria-label="按类型筛选" value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="">全部类型</option><option value="search">原文查询</option><option value="ask">知识问答</option>
          </select>
        </div>
      </div>
      {loading && !data ? <div className="config-loading"><Loader2 className="spin" />正在读取全局记录</div> : !data?.records.length ? <div className="records-empty"><FileSearch size={30} /><h3>暂无记录</h3><p>网页或飞书产生查询、问答后，会在这里显示统一记录。</p></div> : <div className="records-list">{data.records.map((record) => <RecordRow key={record.id} record={record} />)}</div>}
    </section>
  </main>;
}
