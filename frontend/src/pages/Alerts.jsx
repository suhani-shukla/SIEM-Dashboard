// FILE LOCATION: frontend/src/pages/Alerts.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Check, Search, XCircle } from "lucide-react";
import { api } from "../api/client";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import { LoadingState, InlineError, EmptyState } from "../components/common/States";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = ["", "new", "acknowledged", "investigating", "resolved", "false_positive"];
const SEVERITY_OPTIONS = ["", "info", "low", "medium", "high", "critical"];

const QUICK_ACTIONS = {
  new: [{ to: "acknowledged", label: "Acknowledge", icon: Check }],
  acknowledged: [
    { to: "investigating", label: "Investigate", icon: Search },
    { to: "resolved", label: "Resolve", icon: Check },
  ],
  investigating: [
    { to: "resolved", label: "Resolve", icon: Check },
    { to: "false_positive", label: "False positive", icon: XCircle },
  ],
};

export default function Alerts() {
  const [filters, setFilters] = useState({ status: "", severity: "", mitre_technique: "", entity: "" });
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  async function load() {
    setError(null);
    try {
      const res = await api.listAlerts({ ...filters, limit: PAGE_SIZE, offset });
      setData(res);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, offset]);

  function updateFilter(key, value) {
    setOffset(0);
    setFilters((f) => ({ ...f, [key]: value }));
  }

  async function quickAction(alertId, toStatus) {
    setBusyId(alertId);
    try {
      await api.updateAlertStatus(alertId, { status: toStatus, changed_by: "console-user" });
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-base-border bg-base-surface p-4">
        <Select label="Status" value={filters.status} options={STATUS_OPTIONS} onChange={(v) => updateFilter("status", v)} />
        <Select label="Severity" value={filters.severity} options={SEVERITY_OPTIONS} onChange={(v) => updateFilter("severity", v)} />
        <TextInput
          label="MITRE technique"
          value={filters.mitre_technique}
          placeholder="e.g. T1110"
          onChange={(v) => updateFilter("mitre_technique", v)}
        />
        <TextInput
          label="Entity"
          value={filters.entity}
          placeholder="user or IP"
          onChange={(v) => updateFilter("entity", v)}
        />
      </div>

      {error && <InlineError message={error} onRetry={load} />}
      {!error && data === null && <LoadingState label="Loading alerts…" />}

      {!error && data !== null && (
        <div className="overflow-hidden rounded-lg border border-base-border bg-base-surface">
          {data.items.length === 0 ? (
            <EmptyState title="No alerts match these filters" description="Try widening your filters or run a simulation." />
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-base-border bg-base-surface-raised text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Triggered</th>
                  <th className="px-4 py-3 font-medium">Rule</th>
                  <th className="px-4 py-3 font-medium">MITRE</th>
                  <th className="px-4 py-3 font-medium">Entity</th>
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-right">Quick actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-border">
                {data.items.map((alert) => (
                  <tr key={alert.id} className="transition-colors hover:bg-base-hover">
                    <td className="px-4 py-3 font-mono text-xs text-ink-muted whitespace-nowrap">
                      {new Date(alert.triggered_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/alerts/${alert.id}`} className="font-medium text-ink-primary hover:text-brand">
                        {alert.rule_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{alert.mitre_technique || "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{alert.entity || "—"}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={alert.severity} /></td>
                    <td className="px-4 py-3"><StatusBadge status={alert.status} /></td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1.5">
                        {(QUICK_ACTIONS[alert.status] || []).map(({ to, label, icon: Icon }) => (
                          <button
                            key={to}
                            disabled={busyId === alert.id}
                            onClick={() => quickAction(alert.id, to)}
                            title={label}
                            className="flex items-center gap-1 rounded border border-base-border-strong px-2 py-1 text-xs text-ink-secondary hover:border-brand/50 hover:text-brand disabled:opacity-50"
                          >
                            <Icon size={12} />
                            {label}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Pagination */}
          {data.items.length > 0 && (
            <div className="flex items-center justify-between border-t border-base-border px-4 py-3 text-xs text-ink-muted">
              <span className="mono-tabular">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                  className="flex items-center gap-1 rounded border border-base-border-strong px-2 py-1 hover:text-ink-primary disabled:opacity-40"
                >
                  <ChevronLeft size={14} /> Prev
                </button>
                <span className="mono-tabular">
                  Page {page} / {totalPages}
                </span>
                <button
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset((o) => o + PAGE_SIZE)}
                  className="flex items-center gap-1 rounded border border-base-border-strong px-2 py-1 hover:text-ink-primary disabled:opacity-40"
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Select({ label, value, options, onChange }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-ink-muted">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-base-border-strong bg-base-bg px-2.5 py-1.5 text-sm text-ink-primary"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt === "" ? "All" : opt}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextInput({ label, value, placeholder, onChange }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-ink-muted">
      {label}
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-base-border-strong bg-base-bg px-2.5 py-1.5 text-sm text-ink-primary placeholder:text-ink-muted"
      />
    </label>
  );
}
