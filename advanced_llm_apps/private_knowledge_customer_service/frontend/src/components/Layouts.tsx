import {
  BarChart3,
  Blocks,
  Bot,
  Database,
  FileSearch,
  FileText,
  FlaskConical,
  Gauge,
  History,
  Home,
  KeyRound,
  LayoutDashboard,
  MessageSquareText,
  Settings2,
  ShieldCheck,
  UserRound,
  Users,
  Zap,
} from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { identityLabels, useIdentity } from "../identity";

const userNavigation = [
  ["/app/home", "首页", Home],
  ["/app/search", "原文查询", FileSearch],
  ["/app/chat", "知识问答", MessageSquareText],
  ["/app/shortcuts", "快捷入口", Zap],
  ["/app/documents", "文档中心", FileText],
  ["/app/history", "历史记录", History],
] as const;

const adminNavigation = [
  ["/admin/dashboard", "管理首页", LayoutDashboard],
  ["/admin/knowledge", "知识库", Database],
  ["/admin/models", "模型配置", Bot],
  ["/admin/users", "用户管理", Users],
  ["/admin/records", "全局记录", FileText],
  ["/admin/analytics", "数据分析", BarChart3],
  ["/admin/shortcuts", "快捷入口", Zap],
  ["/admin/feishu", "飞书接入", Blocks],
  ["/admin/audit", "审计日志", ShieldCheck],
  ["/admin/retrieval-lab", "检索实验室", FlaskConical],
] as const;

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`product-brand ${compact ? "compact" : ""}`}>
      <div className="product-mark"><KeyRound size={20} aria-hidden="true" /></div>
      {!compact && <div><strong>CoreKnowledge</strong><span>企业私有知识库</span></div>}
    </div>
  );
}

function NavigationLink({ to, label, icon: Icon, compact = false }: {
  to: string;
  label: string;
  icon: typeof Home;
  compact?: boolean;
}) {
  return (
    <NavLink to={to} className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>
      <Icon size={19} aria-hidden="true" />
      <span>{label}</span>
      {compact && <span className="side-tooltip">{label}</span>}
    </NavLink>
  );
}

export function UserLayout() {
  const identity = useIdentity();
  return (
    <div className="product-shell user-shell">
      <aside className="user-sidebar" aria-label="用户端导航">
        <Brand compact />
        <nav>{userNavigation.map(([to, label, icon]) => <NavigationLink compact key={to} to={to} label={label} icon={icon} />)}</nav>
        <div className="sidebar-bottom">
          <NavigationLink compact to="/app/bind-feishu" label="飞书绑定" icon={Blocks} />
          <NavigationLink compact to="/app/profile" label="个人中心" icon={UserRound} />
        </div>
      </aside>
      <div className="product-main">
        <header className="product-topbar">
          <div><span className="eyebrow">企业知识服务</span><strong>{identity.displayName}</strong></div>
          <div className="identity-summary">
            <span className={`identity-dot ${identity.kind}`} />
            <span>{identityLabels[identity.kind]}</span>
            <small>可访问：{identity.visibleScope}</small>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}

export function AdminLayout() {
  return (
    <div className="product-shell admin-shell">
      <aside className="admin-sidebar" aria-label="管理端导航">
        <Brand />
        <nav>{adminNavigation.map(([to, label, icon]) => <NavigationLink key={to} to={to} label={label} icon={icon} />)}</nav>
        <div className="admin-account"><div className="account-avatar">管</div><div><strong>系统管理员</strong><span>本地超级管理员</span></div><Settings2 size={17} /></div>
      </aside>
      <div className="product-main"><Outlet /></div>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{description}</p></div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
