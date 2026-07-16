import { Bot, Copy, FileText, Loader2, LockKeyhole, MessageSquareText, Send, ShieldAlert, Sparkles } from "lucide-react";
import { type FormEvent, useState } from "react";
import { askKnowledge, locationText, type AskResponse, type Provider } from "../api";
import { PageHeader } from "../components/Layouts";
import { useIdentity } from "../identity";

export function ChatPage() {
  const identity = useIdentity();
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState<Provider>("ollama");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = question.trim();
    if (!normalized) return;
    setLoading(true);
    setError("");
    try {
      setResponse(await askKnowledge(normalized, identity.kind === "internal" ? "internal" : "external", provider));
    } catch (caught) {
      setResponse(null);
      setError(caught instanceof Error ? caught.message : "知识问答失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  const insufficient = response && response.citations.length === 0;
  return (
    <main className="page-content chat-page">
      <PageHeader eyebrow="证据驱动" title="知识问答" description="先检索知识库证据，再由当前模型进行总结或汇总；所有答案都应可追溯。" />
      <section className="chat-workspace">
        <div className="conversation-panel">
          {!response && !loading && !error && <div className="chat-welcome"><span><Sparkles size={25} /></span><h2>基于知识库提出问题</h2><p>我只会使用检索到的资料回答。证据不足时会明确告诉你，不会自由编造。</p><div><button onClick={() => setQuestion("客户申请退款的期限是多久？")}>退款期限是什么？</button><button onClick={() => setQuestion("请总结服务时间安排")}>总结服务时间</button></div></div>}
          {loading && <div className="chat-loading"><Loader2 className="spin" size={24} /><strong>正在检索证据并生成回答</strong><p>回答前会先校验你的身份、知识范围与模型隐私策略。</p></div>}
          {error && <div className="chat-message error" role="alert"><ShieldAlert size={19} /><div><strong>暂时无法完成问答</strong><p>{error}</p></div></div>}
          {response && <div className="answer-flow"><article className="question-message"><span>你的问题</span><p>{question}</p></article><article className={`assistant-message ${response.mode === "excerpt_only" ? "excerpt" : ""}`}><header><div><span className="assistant-icon"><Bot size={18} /></span><strong>{response.mode === "excerpt_only" ? "原文检索结果" : "知识库回答"}</strong></div><button onClick={() => void navigator.clipboard.writeText(response.answer)} aria-label="复制回答"><Copy size={16} /></button></header>{response.mode === "excerpt_only" && <div className="privacy-degrade"><LockKeyhole size={17} /><div><strong>敏感内容未发送给云端模型</strong><p>当前策略禁止敏感片段进入云端，因此这里只显示本地原文，不进行总结。</p></div></div>}{insufficient ? <div className="insufficient-answer"><ShieldAlert size={22} /><h3>知识库证据不足</h3><p>{response.answer}</p></div> : <div className="answer-text">{response.answer.replace(/\*\*/g, "").split(/\n\s*\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>}</article></div>}
        </div>
        <aside className="chat-evidence-panel"><div className="evidence-title"><div><span className="eyebrow">回答依据</span><h2>引用来源</h2></div><span>{response?.citations.length || 0} 条</span></div>{!response?.citations.length ? <div className="evidence-empty"><FileText size={27} /><p>{response ? "本次回答没有可用引用。" : "完成问答后，引用会显示在这里。"}</p></div> : <div className="evidence-list">{response.citations.map((citation, index) => <article key={citation.citation}><div><span>[{index + 1}] {citation.source}</span><strong>{citation.partition === "sensitive" ? "敏感" : "公开"}</strong></div><small>{locationText(citation.locator)}</small><p>{citation.evidence}</p></article>)}</div>}</aside>
      </section>
      <form className="chat-composer" onSubmit={submit}><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="输入需要基于知识库回答的问题……" aria-label="知识问答内容" rows={3} /><div className="composer-controls"><div className="model-control"><label htmlFor="chat-provider">回答模型</label><select id="chat-provider" value={provider} onChange={(event) => setProvider(event.target.value as Provider)}><option value="ollama">Ollama 本地模型</option><option value="deepseek">DeepSeek 云端模型</option></select></div><button disabled={loading || !question.trim()}>{loading ? <Loader2 className="spin" size={17} /> : <Send size={17} />}{loading ? "回答中" : "发送问题"}</button></div></form>
    </main>
  );
}
