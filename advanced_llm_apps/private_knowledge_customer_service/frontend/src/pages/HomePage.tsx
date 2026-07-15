import { ArrowRight, FileSearch, LockKeyhole, MessageSquareText, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/Layouts";
import { identityLabels, useIdentity } from "../identity";

export function HomePage() {
  const identity = useIdentity();
  return (
    <main className="page-content home-page">
      <PageHeader
        eyebrow="用户首页"
        title={`你好，${identity.displayName}`}
        description="从原始资料中精确查询，或让模型基于知识库证据为你总结答案。"
      />

      <section className="scope-banner" aria-label="当前身份与知识范围">
        <div className="scope-icon"><ShieldCheck size={22} /></div>
        <div><strong>{identityLabels[identity.kind]} · 当前可访问{identity.visibleScope}</strong><p>{identity.kind === "anonymous" ? "无需绑定即可使用公开知识；绑定飞书后历史可跨设备同步。" : "系统会在每次检索前由服务端校验你的真实权限。"}</p></div>
        <Link to={identity.feishuBound ? "/app/profile" : "/app/bind-feishu"}>{identity.feishuBound ? "查看身份" : "绑定飞书"}<ArrowRight size={15} /></Link>
      </section>

      <section className="entry-grid" aria-label="核心功能入口">
        <Link to="/app/search" className="entry-card search-entry">
          <div className="entry-icon"><FileSearch size={28} /></div>
          <div className="entry-copy"><span>资料原貌</span><h2>原文查询</h2><p>直接查找知识库中的原始内容，不调用大模型，不做改写与推断。</p></div>
          <div className="entry-footer"><span><LockKeyhole size={15} /> 不调用大模型</span><ArrowRight size={20} /></div>
        </Link>
        <Link to="/app/chat" className="entry-card chat-entry">
          <div className="entry-icon"><MessageSquareText size={28} /></div>
          <div className="entry-copy"><span>证据驱动</span><h2>知识问答</h2><p>先检索知识库证据，再由当前模型进行总结或汇总，并展示引用来源。</p></div>
          <div className="entry-footer"><span><Sparkles size={15} /> 基于知识库总结</span><ArrowRight size={20} /></div>
        </Link>
      </section>

      <section className="home-lower-grid">
        <article className="soft-panel"><div><span className="eyebrow">最近使用</span><h3>还没有个人历史</h3><p>{identity.kind === "anonymous" ? "匿名记录会保存在当前浏览器中。完成查询或问答后，可从这里快速返回。" : "你的 Web 与飞书记录会显示在这里。"}</p></div><Link to="/app/history">查看历史<ArrowRight size={15} /></Link></article>
        <article className="soft-panel"><div><span className="eyebrow">快捷入口</span><h3>常用问题会逐步出现</h3><p>系统会结合你的使用频次和管理员配置，生成查询与问答快捷入口。</p></div><Link to="/app/shortcuts">进入快捷入口<ArrowRight size={15} /></Link></article>
      </section>
    </main>
  );
}
