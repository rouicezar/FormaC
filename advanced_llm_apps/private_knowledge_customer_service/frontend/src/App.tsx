import { Navigate, Route, Routes } from "react-router-dom";
import { AdminLayout, UserLayout } from "./components/Layouts";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import RetrievalLab from "./RetrievalLab";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/home" replace />} />
      <Route path="/app" element={<UserLayout />}>
        <Route index element={<Navigate to="home" replace />} />
        <Route path="home" element={<HomePage />} />
        {['search', 'chat', 'shortcuts', 'history', 'documents', 'bind-feishu', 'profile'].map((path) => <Route key={path} path={path} element={<PlaceholderPage />} />)}
      </Route>
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        {['knowledge', 'models', 'users', 'records', 'analytics', 'shortcuts', 'feishu', 'audit'].map((path) => <Route key={path} path={path} element={<PlaceholderPage />} />)}
      </Route>
      <Route path="/admin/retrieval-lab" element={<RetrievalLab />} />
      <Route path="*" element={<Navigate to="/app/home" replace />} />
    </Routes>
  );
}
