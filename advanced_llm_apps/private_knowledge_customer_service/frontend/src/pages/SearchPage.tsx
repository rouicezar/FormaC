import { FileSearch, FileText, Loader2, LockKeyhole, Search, ShieldCheck, X } from "lucide-react";
import { type FormEvent, useState } from "react";
import { locationText, searchOriginals, type Citation, type SearchResponse } from "../api";
import { PageHeader } from "../components/Layouts";
import { useIdentity } from "../identity";

export function SearchPage() {
  const identity = useIdentity();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Citation | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) return;
    setLoading(true);
    setError("");
    setSelected(null);
    try {
      setResponse(await searchOriginals(normalized, identity.kind === "internal" ? "internal" : "external", identity.requesterId));
    } catch (caught) {
      setResponse(null);
      setError(caught instanceof Error ? caught.message : "原文查询失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-content search-page">
      <PageHeader eyebrow="资料原貌" title="原文查询" description="直接检索知识库中的原始内容，不调用大模型，不改写、不总结。" />
      <section className="no-model-notice"><ShieldCheck size={18} /><div><strong>隐私承诺：本页不会调用任何大模型</strong><p>查询词只用于本地混合检索与重排，结果保留文档原文和位置。</p></div><span>可访问：{identity.visibleScope}</span></section>
      <form className="large-search" onSubmit={submit}>
        <Search size={20} aria-hidden="true" />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入要查找的原文，例如：退款期限" aria-label="原文查询内容" />
        {query && <button type="button" className="clear-button" onClick={() => { setQuery(""); setResponse(null); }} aria-label="清空查询"><X size={17} /></button>}
        <button className="search-submit" disabled={loading || !query.trim()}>{loading ? <Loader2 className="spin" size={17} /> : <FileSearch size={17} />}{loading ? "正在查询" : "查询原文"}</button>
      </form>
      {error && <div className="page-error" role="alert">{error}</div>}

      {!response && !loading && !error && <section className="search-welcome"><FileSearch size={32} /><h2>从授权资料中找到准确原文</h2><p>支持 PDF、Word、Markdown、文本、表格和演示文稿。查询结果会标注文档名与页码、行号、工作表或幻灯片位置。</p><div><button onClick={() => setQuery("客户申请退款的期限是多久？")}>退款期限</button><button onClick={() => setQuery("服务时间")}>服务时间</button></div></section>}

      {response && response.total === 0 && <section className="search-welcome empty"><FileText size={32} /><h2>没有找到匹配原文</h2><p>知识库中暂时没有与“{response.query}”相关的资料。请调整关键词，系统不会生成或猜测不存在的内容。</p></section>}

      {response && response.total > 0 && <section className="search-results-layout">
        <div className="result-column"><div className="result-summary"><div><strong>找到 {response.total} 条原文</strong><span>查询：{response.query}</span></div><span><LockKeyhole size={14} /> 未调用模型</span></div>
          <div className="result-list">{response.results.map((result, index) => <button className={`original-result ${selected?.citation === result.citation ? "selected" : ""}`} key={result.citation} onClick={() => setSelected(result)}><div className="result-source"><span><FileText size={15} />{result.source}</span><strong>{result.partition === "sensitive" ? "敏感" : "公开"}</strong></div><p>{result.evidence}</p><div className="result-meta"><span>{locationText(result.locator)}</span><span>原文 {index + 1}</span></div></button>)}</div>
        </div>
        <aside className="original-preview"><div className="preview-heading"><div><span className="eyebrow">原文预览</span><h2>{selected ? selected.source : "选择一条结果"}</h2></div>{selected && <span className={selected.partition}>{selected.partition === "sensitive" ? "敏感资料" : "公开资料"}</span>}</div>{selected ? <><div className="preview-location">{locationText(selected.locator)}</div><blockquote>{selected.evidence}</blockquote><p className="preview-footnote">这是知识库检索到的原始片段，未经过大模型改写。</p></> : <div className="preview-empty"><FileText size={28} /><p>点击左侧结果查看完整原文片段和位置。</p></div>}</aside>
      </section>}
    </main>
  );
}
