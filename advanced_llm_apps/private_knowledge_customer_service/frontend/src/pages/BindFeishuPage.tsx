import { Link2, Loader2, ShieldCheck } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { bindAppFeishuProfile } from "../api";
import { PageHeader } from "../components/Layouts";
import { useIdentity } from "../identity";

export function BindFeishuPage() {
  const identity = useIdentity();
  const navigate = useNavigate();
  const [feishuUserId, setFeishuUserId] = useState(identity.feishuUserId || "");
  const [displayName, setDisplayName] = useState(identity.displayName === "访客" ? "" : identity.displayName);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!feishuUserId.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const profile = await bindAppFeishuProfile({
        requesterId: identity.requesterId,
        feishuUserId: feishuUserId.trim(),
        displayName: displayName.trim() || "飞书用户",
      });
      identity.updateFromProfile(profile);
      setMessage(profile.role === "internal" ? "飞书身份已绑定，当前已具备内部访问权限。" : "飞书身份已绑定，并按安全默认设置为外部用户。");
      setTimeout(() => navigate("/app/profile"), 600);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "飞书绑定失败。");
    } finally {
      setBusy(false);
    }
  }

  return <main className="page-content bind-page">
    <PageHeader eyebrow="飞书绑定" title="绑定飞书身份" description="绑定后默认仍是外部用户；只有管理员明确提权后才可访问敏感知识。" />
    {error && <div className="config-alert error" role="alert">{error}</div>}
    {message && <div className="config-alert success"><ShieldCheck size={16} />{message}</div>}
    <form className="profile-panel bind-form" onSubmit={submit}>
      <div className="config-card-title"><Link2 /><div><h2>身份信息</h2><p>请填写飞书 open_id。真实 OAuth 接入前，这里用于测试 Web 与飞书记录合并。</p></div></div>
      <label>显示名称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="例如：王小明" /></label>
      <label>飞书 open_id<input required value={feishuUserId} onChange={(event) => setFeishuUserId(event.target.value)} placeholder="例如：ou_xxxxxxxxx" /></label>
      <button className="primary-action" disabled={busy || !feishuUserId.trim()}>{busy ? <Loader2 className="spin" size={16} /> : <Link2 size={16} />}{busy ? "正在绑定" : "绑定并同步身份"}</button>
    </form>
  </main>;
}
