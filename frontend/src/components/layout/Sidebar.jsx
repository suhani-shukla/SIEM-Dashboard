// FILE LOCATION: frontend/src/components/layout/Sidebar.jsx
import { NavLink } from "react-router-dom";
import { LayoutDashboard, ShieldAlert, ScrollText, Grid3x3 } from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/alerts", label: "Alerts", icon: ShieldAlert },
  { to: "/events", label: "Log Viewer", icon: ScrollText },
  { to: "/playbooks", label: "Playbooks", icon: Grid3x3 },
];

export default function Sidebar() {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-base-border bg-base-surface">
      <div className="flex h-14 items-center gap-2 border-b border-base-border px-5">
        <span className="h-2 w-2 rounded-full bg-brand shadow-glow" />
        <span className="font-mono text-sm font-semibold tracking-wide text-ink-primary">
          SIEM<span className="text-brand">//</span>console
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 p-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-brand/10 font-medium text-brand"
                  : "text-ink-secondary hover:bg-base-hover hover:text-ink-primary"
              }`
            }
          >
            <Icon size={16} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-base-border p-4 text-[11px] text-ink-muted">
        <p className="font-mono">v0.6.0 · phase 6</p>
      </div>
    </aside>
  );
}
