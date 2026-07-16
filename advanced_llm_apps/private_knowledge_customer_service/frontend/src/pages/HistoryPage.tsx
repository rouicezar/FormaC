import { FileSearch, Loader2, MessageSquareText, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getPersonalRecords, locationText, type InteractionRecord, type PersonalRecordList } from "../api";
import { PageHeader } from "../components/Layouts";
import { identityLabels, useIdentity } from "../identity";

const kindText = { search: "原文查询", ask: "知识问答" };
const channelText = { web: "网页", feishu: "飞书" };

function excerpt(record: InteractionRecord) {
  const text = record.kind === "ask" ? record.answer || "" : record.citations[0]?.evidence || "";
  if (!text) return record.kind === "ask" ? "本次问答没有返回正文。" : "本次查询没有命中原文。";
  return text.length > 110 ? `${text.slice(0, 110)}...` : text;
}

function HistoryRow({ record }: { record: InteractionRecord }) {
  const firstCitation = record.citations[0];
  return <article className="record-row history-row">
    <div className="record-kind-icon">{record.kind === "search" ? <FileSearch size={17} /> : <MessageSquareText size={17} />}</div>
    <div className="record-main">
      <div className="record-title">
        <strong>{record.query}</strong>
        <span>{channelText[record.channel]} · {kindText[record.kind]}</span>
      </div>
      <p>{excerpt(record)}</p>
      <div className="record-meta">
        <span>{new Date(record.created_at).toLocaleString("zh-CN")}</span>
        <span>引用：{record.citations.length}</span>
        {firstCitation && <span>{firstCitation.source} · {locationText(firstCitation.locator)}</span>}
      </div>
    </div>
  </article>;
}

export function HistoryPage() {
  const identity = useIdentity();
  const [data, setData] = useState<PersonalRecordList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [kind, setKind] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getPersonalRecords(identity.requesterId, { kind, feishuUserId: identity.feishuUserId }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "个人历史读取失败。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [identity.requesterId, identity.feishuUserId, kind]);

  const metrics = useMemo(() => data?.stats || {
    total: 0, search: 0, ask: 0, web: 0, feishu: 0, citations: 0,
  }, [data]);

  return <main className="page-content app-history-page">
    <PageHeader
      eyebrow="个人记录"
      title="我的历史"
      description="只展示当前浏览器身份对应的查询与问答记录；全局记录仅管理员可见。"
      actions={<button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""} />刷新</button>}
    />
    <section className="history-identity-card">
      <ShieldCheck size={20} />
      <div>
        <strong>{identityLabels[identity.kind]} · {identity.displayName}</strong>
        <p>当前记录归属：<code>{identity.requesterId}</code>{identity.feishuUserId ? <> 和 <code>{identity.feishuUserId}</code></> : null}。{identity.feishuBound ? "已合并网页与飞书记录。" : "匿名记录保存在当前浏览器身份下。"}</p>
      </div>
      <span>可访问：{identity.visibleScope}</span>
    </section>
    {error && <div className="config-alert error" role="alert">{error}</div>}
    <section className="record-metric-grid">
      <article><span>我的记录</span><strong>{metrics.total}</strong></article>
      <article><span>原文查询</span><strong>{metrics.search}</strong></article>
      <article><span>知识问答</span><strong>{metrics.ask}</strong></article>
      <article><span>引用总数</span><strong>{metrics.citations}</strong></article>
    </section>
    <section className="records-panel">
      <div className="records-toolbar">
        <div><h2>个人交互明细</h2><p>记录来源于网页端，后续飞书绑定后会按同一身份规则合并展示。</p></div>
        <div>
          <select aria-label="按类型筛选个人历史" value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="">全部类型</option>
            <option value="search">原文查询</option>
            <option value="ask">知识问答</option>
          </select>
        </div>
      </div>
      {loading && !data ? <div className="config-loading"><Loader2 className="spin" />正在读取个人历史</div> : !data?.records.length ? <div className="records-empty"><FileSearch size={30} /><h3>还没有个人历史</h3><p>完成原文查询或知识问答后，本页会显示你的个人记录和引用统计。</p></div> : <div className="records-list">{data.records.map((record) => <HistoryRow key={record.id} record={record} />)}</div>}
    </section>
  </main>;
}
