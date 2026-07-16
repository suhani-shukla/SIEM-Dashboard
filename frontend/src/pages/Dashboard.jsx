// FILE LOCATION: frontend/src/pages/Dashboard.jsx
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { PlayCircle, Loader2 } from "lucide-react";
import { api } from "../api/client";
import { useAlertStreamContext } from "../components/layout/AppLayout";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import { LoadingState, InlineError, EmptyState } from "../components/common/States";

const SIM_BUTTONS = [
  { attack_type: "brute_force", label: "Brute Force" },
  { attack_type: "dns_tunneling", label: "DNS Tunneling" },
  { attack_type: "phishing", label: "Phishing" },
  { attack_type: "privilege_escalation", label: "Privilege Escalation" },
];

function startOfTodayISO() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

function hoursAgoISO(hours) {
  return new Date(Date.now() - hours * 3600_000).toISOString();
}

export default function Dashboard() {
  const { alerts: liveAlerts, connected } = useAlertStreamContext();
  const [todayAlerts, setTodayAlerts] = useState(null);
  const [recentAlerts, setRecentAlerts] = useState(null);
  const [volumeSeries, setVolumeSeries] = useState(null);
  const [error, setError] = useState(null);
  const [simRunning, setSimRunning] = useState(null);

  async function loadAll() {
    setError(null);
    try {
      const [todayRes, recentRes, eventsRes] = await Promise.all([
        api.listAlerts({ date_from: startOfTodayISO(), limit: 500 }),
        api.listAlerts({ limit: 8 }),
        api.listEvents({ date_from: hoursAgoISO(24), limit: 500 }),
      ]);
      setTodayAlerts(todayRes.items);
      setRecentAlerts(recentRes.items);
      setVolumeSeries(bucketEventsByHour(eventsRes.items));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 30000);
    return () => clearInterval(interval);
  }, []);

  // merge live SSE alerts on top of the polled "recent" list for the feed panel
  const feed = useMemo(() => {
    if (!recentAlerts) return liveAlerts;
    const liveIds = new Set(liveAlerts.map((a) => a.id));
    const merged = [...liveAlerts, ...recentAlerts.filter((a) => !liveIds.has(a.id))];
    return merged.slice(0, 12);
  }, [liveAlerts, recentAlerts]);

  const severityCounts = useMemo(() => countBy(todayAlerts, "severity"), [todayAlerts]);
  const statusCounts = useMemo(() => countBy(todayAlerts, "status"), [todayAlerts]);

  async function runSimulation(attack_type) {
    setSimRunning(attack_type);
    try {
      await api.triggerSimulation({ attack_type, mode: "fast", noise_events: 15 });
      setTimeout(loadAll, 2500);
    } catch (e) {
      setError(e.message);
    } finally {
      setTimeout(() => setSimRunning(null), 2000);
    }
  }

  if (error) return <InlineError message={error} onRetry={loadAll} />;
  if (todayAlerts === null) return <LoadingState label="Loading dashboard…" />;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard label="Alerts today" value={todayAlerts.length} />
        <SummaryCard
          label="By severity"
          value={
            <div className="flex flex-wrap gap-1.5">
              {["critical", "high", "medium", "low", "info"].map((s) =>
                severityCounts[s] ? (
                  <span key={s} className="flex items-center gap-1 text-xs">
                    <SeverityBadge severity={s} />
                    <span className="mono-tabular text-ink-secondary">{severityCounts[s]}</span>
                  </span>
                ) : null
              )}
            </div>
          }
        />
        <SummaryCard
          label="Open / investigating"
          value={(statusCounts.new || 0) + (statusCounts.investigating || 0) + (statusCounts.acknowledged || 0)}
        />
        <SummaryCard label="Resolved today" value={statusCounts.resolved || 0} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Event volume chart */}
        <div className="xl:col-span-2 rounded-lg border border-base-border bg-base-surface p-5">
          <h2 className="mb-4 text-sm font-medium text-ink-secondary">Event volume — last 24h</h2>
          {volumeSeries && volumeSeries.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={volumeSeries}>
                <defs>
                  <linearGradient id="volGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2DD4BF" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#2DD4BF" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#232C38" vertical={false} />
                <XAxis dataKey="hour" stroke="#5E6B78" fontSize={11} tickLine={false} />
                <YAxis stroke="#5E6B78" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: "#171F2A",
                    border: "1px solid #232C38",
                    borderRadius: 8,
                    fontSize: 12,
                    fontFamily: "IBM Plex Mono, monospace",
                  }}
                />
                <Area type="monotone" dataKey="count" stroke="#2DD4BF" fill="url(#volGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No event data yet" description="Run a simulation to populate the timeline." />
          )}
        </div>

        {/* Live feed panel */}
        <div className="rounded-lg border border-base-border bg-base-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-medium text-ink-secondary">Live alert feed</h2>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400 animate-pulse-dot" : "bg-severity-critical"}`} />
          </div>
          <div className="space-y-1 overflow-y-auto" style={{ maxHeight: 320 }}>
            {feed.length === 0 && (
              <EmptyState title="No alerts yet" description="Trigger a simulation below to see live alerts." />
            )}
            {feed.map((alert) => (
              <Link
                key={alert.id}
                to={`/alerts/${alert.id}`}
                className="flex items-center justify-between gap-2 rounded-md px-2 py-2 text-xs hover:bg-base-hover animate-flash-in"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink-primary">{alert.rule_name}</p>
                  <p className="truncate font-mono text-ink-muted">{alert.entity || "—"}</p>
                </div>
                <SeverityBadge severity={alert.severity} />
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Simulation triggers */}
      <div className="rounded-lg border border-base-border bg-base-surface p-5">
        <h2 className="mb-1 text-sm font-medium text-ink-secondary">Run a simulation</h2>
        <p className="mb-4 text-xs text-ink-muted">
          Generates a realistic multi-stage attack and feeds it through the live pipeline.
        </p>
        <div className="flex flex-wrap gap-3">
          {SIM_BUTTONS.map(({ attack_type, label }) => (
            <button
              key={attack_type}
              onClick={() => runSimulation(attack_type)}
              disabled={simRunning === attack_type}
              className="flex items-center gap-2 rounded-md border border-base-border-strong bg-base-hover px-3.5 py-2 text-xs font-medium text-ink-primary transition-colors hover:border-brand/50 hover:text-brand disabled:opacity-60"
            >
              {simRunning === attack_type ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <PlayCircle size={14} />
              )}
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div className="rounded-lg border border-base-border bg-base-surface p-4">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
      <div className="text-2xl font-semibold mono-tabular text-ink-primary">{value}</div>
    </div>
  );
}

function countBy(items, field) {
  return (items || []).reduce((acc, item) => {
    acc[item[field]] = (acc[item[field]] || 0) + 1;
    return acc;
  }, {});
}

function bucketEventsByHour(events) {
  const buckets = {};
  for (const e of events) {
    const d = new Date(e.timestamp);
    d.setMinutes(0, 0, 0);
    const key = d.toISOString();
    buckets[key] = (buckets[key] || 0) + 1;
  }
  return Object.entries(buckets)
    .sort(([a], [b]) => new Date(a) - new Date(b))
    .map(([key, count]) => ({
      hour: new Date(key).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      count,
    }));
}
