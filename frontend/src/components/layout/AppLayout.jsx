// FILE LOCATION: frontend/src/components/layout/AppLayout.jsx
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { useAlertStream } from "../../hooks/useSSE";
import { createContext, useContext } from "react";

const PAGE_TITLES = {
  "/dashboard": "Overview",
  "/alerts": "Alerts",
  "/events": "Log Viewer",
  "/playbooks": "Playbooks",
};

const AlertStreamContext = createContext(null);
export const useAlertStreamContext = () => useContext(AlertStreamContext);

export default function AppLayout() {
  const location = useLocation();
  const stream = useAlertStream({ maxBuffered: 50 });

  const title =
    Object.entries(PAGE_TITLES).find(([path]) => location.pathname.startsWith(path))?.[1] ||
    "SIEM Console";

  return (
    <AlertStreamContext.Provider value={stream}>
      <div className="flex h-screen overflow-hidden bg-base-bg">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar title={title} connected={stream.connected} lastAlertAt={stream.lastAlertAt} />
          <main className="flex-1 overflow-y-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </AlertStreamContext.Provider>
  );
}
