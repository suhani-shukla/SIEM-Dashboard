// FILE LOCATION: frontend/src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import ErrorBoundary from "./components/common/ErrorBoundary";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import AlertDetail from "./pages/AlertDetail";
import EventsLogViewer from "./pages/EventsLogViewer";
import Playbooks from "./pages/Playbooks";

function withBoundary(element) {
  return <ErrorBoundary>{element}</ErrorBoundary>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={withBoundary(<Dashboard />)} />
        <Route path="alerts" element={withBoundary(<Alerts />)} />
        <Route path="alerts/:id" element={withBoundary(<AlertDetail />)} />
        <Route path="events" element={withBoundary(<EventsLogViewer />)} />
        <Route path="playbooks" element={withBoundary(<Playbooks />)} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
