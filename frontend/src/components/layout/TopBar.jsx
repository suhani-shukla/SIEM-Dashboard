// FILE LOCATION: frontend/src/components/layout/TopBar.jsx
import { useEffect, useState } from "react";

export default function TopBar({ title, connected, lastAlertAt }) {
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (!lastAlertAt) return;
    setFlash(true);
    const t = setTimeout(() => setFlash(false), 600);
    return () => clearTimeout(t);
  }, [lastAlertAt]);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-base-border bg-base-surface px-6">
      <h1 className="text-sm font-semibold text-ink-primary">{title}</h1>

      <div className="flex items-center gap-2 rounded-full border border-base-border bg-base-bg px-3 py-1.5">
        <span
          className={`h-2 w-2 rounded-full transition-transform ${
            connected ? "bg-emerald-400" : "bg-severity-critical"
          } ${flash ? "scale-150" : ""} ${connected ? "animate-pulse-dot" : ""}`}
        />
        <span className="font-mono text-xs text-ink-secondary">
          {connected ? "Live feed connected" : "Reconnecting…"}
        </span>
      </div>
    </header>
  );
}
