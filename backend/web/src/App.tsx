import { Routes, Route, Navigate } from 'react-router-dom';
import { useAppStore } from './stores/app';
import MainLayout from './components/MainLayout';
import Login from './pages/login';
import Dashboard from './pages/dashboard';
import PublishRecords from './pages/publish-records';
import Channels from './pages/channels';
import Config from './pages/config';
import Alerts from './pages/alerts';
import SpotCheck from './pages/spot-check';
import UnmannedReport from './pages/unmanned-report';
import ApiKeys from './pages/apikeys';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((s) => !!s.token);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="publish-records" element={<PublishRecords />} />
        <Route path="channels" element={<Channels />} />
        <Route path="config" element={<Config />} />
        <Route path="apikeys" element={<ApiKeys />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="spot-check" element={<SpotCheck />} />
        <Route path="unmanned-report" element={<UnmannedReport />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}