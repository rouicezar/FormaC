import { Link2, Loader2, RefreshCw, ShieldCheck, ShieldMinus, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAppProfile, type AppProfile } from "../api";
import { PageHeader } from "../components/Layouts";
import { useIdentity } from "../identity";

export function ProfilePage() {
  const identity = useIdentity();
  const [profile, setProfile] = useState<AppProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const next = await getAppProfile(identity.requesterId, identity.feishuUserId, identity.displayName);
      setProfile(next);
      identity.updateFromProfile(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "个人身份读取失败。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [identity.requesterId, identity.feishuUserId]);

  const role = profile?.role || identity.kind;
  const roleLabel = role === "internal" ? "内部员工" : role === "external" ? "外部用户" : "匿名访客";
  const bound = profile?.feishu_bound ?? identity.feishuBound;
  return <main className="page-content profile-page">
    <PageHeader eyebrow="个人中心" title="我的身份" description="查看当前浏览器身份、飞书绑定和服务端授权范围。" actions={<button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""} />刷新身份</button>} />
    {error && <div className="config-alert error" role="alert">{error}</div>}
    {loading && !profile ? <div className="config-loading"><Loader2 className="spin" />正在读取个人身份</div> : <section className="profile-grid">
      <article className="profile-card featured-profile">
        <UserRound />
        <span>当前身份</span>
        <strong>{roleLabel}</strong>
        <p>{profile?.display_name || identity.displayName}</p>
      </article>
      <article className="profile-card">
        {bound ? <ShieldCheck /> : <ShieldMinus />}
        <span>飞书绑定</span>
        <strong>{bound ? "已绑定" : "未绑定"}</strong>
        <p>{profile?.feishu_user_id || "绑定后可合并飞书与网页历史。"}</p>
      </article>
      <article className="profile-card">
        <ShieldCheck />
        <span>可访问范围</span>
        <strong>{profile?.visible_scope || identity.visibleScope}</strong>
        <p>服务端会在每次查询和问答前重新校验权限。</p>
      </article>
    </section>}
    <section className="profile-panel">
      <div className="section-heading"><div><h2>身份映射</h2><p>浏览器 requester 与飞书 open_id 会共同决定个人历史归属；管理员授权决定外部/内部身份。</p></div></div>
      <div className="mapping-list">
        <div><span>浏览器 requester</span><code>{identity.requesterId}</code></div>
        <div><span>飞书 open_id</span><code>{profile?.feishu_user_id || identity.feishuUserId || "尚未绑定"}</code></div>
        <div><span>个人记录</span><strong>{profile?.records.total ?? 0} 条</strong></div>
        <div><span>飞书来源</span><strong>{profile?.records.feishu ?? 0} 条</strong></div>
      </div>
      {!bound && <Link className="profile-bind-link" to="/app/bind-feishu"><Link2 size={16} />绑定飞书身份</Link>}
    </section>
  </main>;
}
