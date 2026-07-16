import { Navigate, Route, Routes } from "react-router-dom";
import { AdminLayout, UserLayout } from "./components/Layouts";
import { DashboardPage } from "./pages/DashboardPage";
import { ChatPage } from "./pages/ChatPage";
import { HomePage } from "./pages/HomePage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { SearchPage } from "./pages/SearchPage";
import RetrievalLab from "./RetrievalLab";
import { KnowledgePage } from "./pages/KnowledgePage";
import { ModelsPage } from "./pages/ModelsPage";
import { UsersPage } from "./pages/UsersPage";
import { FeishuPage } from "./pages/FeishuPage";
import { RecordsPage } from "./pages/RecordsPage";
import { HistoryPage } from "./pages/HistoryPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/home" replace />} />
      <Route path="/app" element={<UserLayout />}>
        <Route index element={<Navigate to="home" replace />} />
        <Route path="home" element={<HomePage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="history" element={<HistoryPage />} />
        {['shortcuts', 'documents', 'bind-feishu', 'profile'].map((path) => <Route key={path} path={path} element={<PlaceholderPage />} />)}
      </Route>
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="feishu" element={<FeishuPage />} />
        <Route path="records" element={<RecordsPage />} />
        {['analytics', 'shortcuts', 'audit'].map((path) => <Route key={path} path={path} element={<PlaceholderPage />} />)}
      </Route>
      <Route path="/admin/retrieval-lab" element={<RetrievalLab />} />
      <Route path="*" element={<Navigate to="/app/home" replace />} />
    </Routes>
  );
}
