import { ArrowLeft, Construction } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { PageHeader } from "../components/Layouts";

const pageNames: Record<string, string> = {
  "/app/search": "原文查询", "/app/chat": "知识问答", "/app/shortcuts": "快捷入口", "/app/history": "历史记录", "/app/documents": "文档中心", "/app/bind-feishu": "飞书绑定", "/app/profile": "个人中心",
  "/admin/knowledge": "知识库管理", "/admin/models": "模型配置", "/admin/users": "用户管理", "/admin/records": "全局记录", "/admin/analytics": "数据分析", "/admin/shortcuts": "快捷入口管理", "/admin/feishu": "飞书接入", "/admin/audit": "审计日志",
};

export function PlaceholderPage() {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith("/admin");
  const title = pageNames[location.pathname] || "页面建设中";
  return <main className="page-content"><PageHeader eyebrow={isAdmin ? "管理端" : "用户端"} title={title} description="正式路由已经建立，业务能力将在对应实施阶段接入。" /><section className="placeholder-panel"><Construction size={30} /><h2>该页面尚未进入本阶段实现范围</h2><p>这不是独立预览页面。它已经处于正式产品路由与导航中，后续会在同一工程内接入真实 API。</p><Link to={isAdmin ? "/admin/dashboard" : "/app/home"}><ArrowLeft size={16} />返回{isAdmin ? "管理首页" : "用户首页"}</Link></section></main>;
}
