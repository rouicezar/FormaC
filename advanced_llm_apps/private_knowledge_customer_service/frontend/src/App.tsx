import {
  Activity,
  Bot,
  BrainCircuit,
  Database,
  FileSearch,
  FileText,
  FolderSync,
  Loader2,
  LockKeyhole,
  MessageSquare,
  Send,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8897";

type Identity = "external" | "internal";
type Provider = "deepseek" | "ollama";

type ScanReport = {
  id: string;
  status: string;
  added: number;
  updated: number;
  deleted: number;
  failed: number;
  skipped: number;
  errors: Array<{ path: string; error: string }>;
};

type Citation = {
  citation: string;
  source: string;
  similarity: number;
  evidence: string;
  partition: "public" | "sensitive";
  locator: Record<string, unknown>;
};

type AskResponse = {
  answer: string;
  mode: "generate" | "excerpt_only";
  citations: Citation[];
};

function locationText(locator: Record<string, unknown>) {
  if (locator.page) return `第 ${locator.page} 页`;
  if (locator.sheet) {
    const range = locator.cell_range ? ` · 单元格 ${locator.cell_range}` : "";
    return `工作表 ${locator.sheet}${range}`;
  }
  if (locator.slide) return `第 ${locator.slide} 张幻灯片`;
  if (locator.paragraph) return `第 ${locator.paragraph} 段`;
  if (locator.line_start) {
    const end = locator.line_end && locator.line_end !== locator.line_start
      ? `–${locator.line_end}`
      : "";
    return `第 ${locator.line_start}${end} 行`;
  }
  return "文档原文";
}

function AnswerContent({ answer }: { answer: string }) {
  if (!answer) return <p>完成扫描后输入问题，回答会显示在这里。</p>;
  return (
    <div className="answer-content">
      {answer.split(/\n\s*\n/).filter(Boolean).map((block, index) => (
        <p key={index}>{block}</p>
      ))}
    </div>
  );
}

export default function App() {
  const [connected, setConnected] = useState(false);
  const [scan, setScan] = useState<ScanReport | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [identity, setIdentity] = useState<Identity>("external");
  const [provider, setProvider] = useState<Provider>("ollama");
  const [allowSensitiveCloud, setAllowSensitiveCloud] = useState(false);
  const [question, setQuestion] = useState("客户申请退款的期限是多久？");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [askError, setAskError] = useState("");

  useEffect(() => {
    fetch(`${API}/health`)
      .then((response) => {
        if (!response.ok) throw new Error();
        setConnected(true);
      })
      .catch(() => setConnected(false));
  }, []);

  async function startScan() {
    setIsScanning(true);
    setScanError("");
    try {
      const response = await fetch(`${API}/admin/scans`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "扫描失败，请检查服务配置。");
      setScan(data);
    } catch (error) {
      setScanError(error instanceof Error ? error.message : "扫描失败，请检查服务配置。");
    } finally {
      setIsScanning(false);
    }
  }

  async function askQuestion() {
    if (!question.trim()) return;
    setIsAsking(true);
    setAskError("");
    setResult(null);
    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          identity,
          provider,
          allow_sensitive_cloud: allowSensitiveCloud,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "问答失败，请检查模型配置。");
      setResult(data);
    } catch (error) {
      setAskError(error instanceof Error ? error.message : "问答失败，请检查模型配置。");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><BrainCircuit size={22} /></div>
          <div>
            <h1>私有知识库客服台</h1>
            <p>本地文档索引 · 权限隔离 · 可核查引用</p>
          </div>
        </div>
        <div className="status-strip">
          <span><Activity size={14} /> {connected ? "后端已连接" : "后端未连接"}</span>
          <span><Database size={14} /> PostgreSQL + pgvector</span>
          <span><ShieldCheck size={14} /> 敏感云端默认关闭</span>
        </div>
      </header>

      <section className="workspace">
        <aside className="left-rail">
          <section className="panel source-panel">
            <div className="panel-heading">
              <div>
                <h2>本地知识目录</h2>
                <p>读取服务端已授权目录，不上传任何文件。</p>
              </div>
              <FolderSync size={18} />
            </div>
            <div className="folder-card public-folder">
              <FileText size={17} />
              <div><strong>公开文档</strong><span>public/ · 外部与内部身份均可检索</span></div>
            </div>
            <div className="folder-card sensitive-folder">
              <LockKeyhole size={17} />
              <div><strong>敏感文档</strong><span>sensitive/ · 仅内部测试身份可检索</span></div>
            </div>
            <button className="primary-button" onClick={startScan} disabled={isScanning}>
              {isScanning ? <Loader2 className="spin" size={16} /> : <FolderSync size={16} />}
              {isScanning ? "正在增量扫描……" : "立即扫描知识目录"}
            </button>
            {scanError && <div className="inline-status error" role="alert">{scanError}</div>}
          </section>

          <section className="panel source-list">
            <div className="panel-heading">
              <div><h2>最近扫描结果</h2><p>仅显示本次新增、变化和错误。</p></div>
              <FileSearch size={18} />
            </div>
            {!scan && <div className="empty-state">尚未手动扫描。</div>}
            {scan && (
              <>
                <div className="scan-grid">
                  <span><strong>{scan.added}</strong>新增</span>
                  <span><strong>{scan.updated}</strong>更新</span>
                  <span><strong>{scan.deleted}</strong>删除</span>
                  <span><strong>{scan.skipped}</strong>未变化</span>
                </div>
                <div className={`inline-status ${scan.failed ? "error" : "success"}`} role="status">
                  {scan.failed ? `${scan.failed} 个文件处理失败` : "扫描完成，索引已同步。"}
                </div>
                {scan.errors.map((error) => (
                  <div className="scan-error" key={error.path}>
                    <strong>{error.path}</strong><span>{error.error}</span>
                  </div>
                ))}
              </>
            )}
          </section>
        </aside>

        <section className="space-stage qa-stage">
          <div className="stage-header">
            <div>
              <h2>基于知识库提问</h2>
              <p>回答只能使用本地检索到的证据；没有证据时不会自由发挥。</p>
            </div>
            <span className={`mode-badge ${result?.mode === "excerpt_only" ? "excerpt" : ""}`}>
              {result?.mode === "excerpt_only" ? "原文模式" : "知识回答"}
            </span>
          </div>
          <div className="qa-composer">
            <textarea
              className="question-box"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              aria-label="请输入知识库问题"
            />
            <button className="primary-button" onClick={askQuestion} disabled={isAsking}>
              {isAsking ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
              {isAsking ? "正在检索并回答……" : "发送问题"}
            </button>
          </div>
          {askError && <div className="inline-status error" role="alert">{askError}</div>}
          <div className="answer-box prominent-answer">
            <MessageSquare size={17} />
            <AnswerContent answer={result?.answer || ""} />
          </div>
        </section>

        <aside className="right-rail">
          <section className="panel qa-panel">
            <div className="panel-heading">
              <div><h2>问答设置</h2><p>用于手动验收权限和隐私边界。</p></div>
              <Bot size={18} />
            </div>
            <label className="field-label" htmlFor="identity">测试身份</label>
            <select id="identity" value={identity} onChange={(event) => setIdentity(event.target.value as Identity)}>
              <option value="external">外部客户（仅公开文档）</option>
              <option value="internal">内部员工（公开与敏感文档）</option>
            </select>
            <label className="field-label" htmlFor="provider">回答模型</label>
            <select id="provider" value={provider} onChange={(event) => setProvider(event.target.value as Provider)}>
              <option value="ollama">Ollama 本地模型</option>
              <option value="deepseek">DeepSeek 云端模型</option>
            </select>
            <label className={`privacy-toggle ${provider !== "deepseek" ? "disabled" : ""}`}>
              <input
                type="checkbox"
                checked={allowSensitiveCloud}
                disabled={provider !== "deepseek"}
                onChange={(event) => setAllowSensitiveCloud(event.target.checked)}
              />
              <span><strong>允许敏感原文发送到云端</strong><small>默认关闭；关闭时只返回本地检索原文。</small></span>
            </label>
          </section>

          <section className="panel citations-panel">
            <div className="panel-heading">
              <div><h2>引用来源</h2><p>核查文件、分区和原文位置。</p></div>
            </div>
            {!result?.citations.length && <div className="empty-state">还没有引用记录。</div>}
            <div className="citation-list">
              {result?.citations.map((citation, index) => (
                <article className="citation-row" key={citation.citation}>
                  <div className="citation-top">
                    <span><FileText size={14} /> [{index + 1}] {citation.source}</span>
                    <strong>{citation.partition === "sensitive" ? "敏感" : "公开"}</strong>
                  </div>
                  <div className="citation-location">{locationText(citation.locator)}</div>
                  <p>{citation.evidence}</p>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
