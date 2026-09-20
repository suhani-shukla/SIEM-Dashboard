// FILE LOCATION: frontend/src/pages/EventsLogViewer.jsx
import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronDown, ChevronRight, ChevronLeft, Search } from "lucide-react";
import { api } from "../api/client";
import SeverityBadge from "../components/common/SeverityBadge";
import JsonView from "../components/common/JsonView";
import { LoadingState, InlineError, EmptyState } from "../components/common/States";

const PAGE_SIZE = 50;
const SEVERITY_OPTIONS = ["", "info", "low", "medium", "high", "critical"];

export default function EventsLogViewer() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [filters, setFilters] = useState({
    date_from: searchParams.get("date_from") || "",
    date_to: searchParams.get("date_to") || "",
    severity: searchParams.get("severity") || "",
    source: searchParams.get("source") || "",
    event_type: searchParams.get("event_type") || "",
    q: searchParams.get("q") || "",
  });
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  async function load() {
    setError(null);
    try {
      const res = await api.listEvents({ ...filters, limit: PAGE_SIZE, offset });
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
    const next = { ...filters, [key]: value };
    setFilters(next);
    setSearchParams(Object.fromEntries(Object.entries(next).filter(([, v]) => v)));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-base-border bg-base-surface p-4">
        <TextInput label="From" type="datetime-local" value={filters.date_from} onChange={(v) => updateFilter("date_from", v)} />
        <TextInput label="To" type="datetime-local" value={filters.date_to} onChange={(v) => updateFilter("date_to", v)} />
        <Select label="Severity" value={filters.severity} options={SEVERITY_OPTIONS} onChange={(v) => updateFilter("severity", v)} />
        <TextInput label="Source" value={filters.source} placeholder="e.g. ssh" onChange={(v) => updateFilter("source", v)} />
        <TextInput label="Event type" value={filters.event_type} placeholder="e.g. auth_failure" onChange={(v) => updateFilter("event_type", v)} />
        <div className="flex flex-col gap-1 text-xs text-ink-muted">
          Search
          <div className="flex items-center gap-1.5 rounded border border-base-border-strong bg-base-bg px-2.5 py-1.5">
            <Search size={13} className="text-ink-muted" />
            <input
              value={filters.q}
              placeholder="search raw payload…"
              onChange={(e) => updateFilter("q", e.target.value)}
              className="w-40 bg-transparent text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none"
            />
          </div>
        </div>
      </div>

      {error && <InlineError message={error} onRetry={load} />}
      {!error && data === null && <LoadingState label="Loading events…" />}

      {!error && data !== null && (
        <div className="overflow-hidden rounded-lg border border-base-border bg-base-surface">
          {data.items.length === 0 ? (
            <EmptyState title="No events match these filters" description="Adjust filters or ingest/simulate more data." />
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-base-border bg-base-surface-raised text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="w-8 px-3 py-3"></th>
                  <th className="px-3 py-3 font-medium">Timestamp</th>
                  <th className="px-3 py-3 font-medium">Source</th>
                  <th className="px-3 py-3 font-medium">Event type</th>
                  <th className="px-3 py-3 font-medium">Severity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-border">
                {data.items.map((ev) => {
                  const expanded = expandedId === ev.id;
                  return (
                    <Fragment key={ev.id}>
                      <tr
                        key={ev.id}
                        onClick={() => setExpandedId(expanded ? null : ev.id)}
                        className="cursor-pointer transition-colors hover:bg-base-hover"
                      >
                        <td className="px-3 py-2.5 text-ink-muted">
                          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-xs text-ink-secondary whitespace-nowrap">
                          {new Date(ev.timestamp).toLocaleString()}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-xs text-ink-secondary">{ev.source}</td>
                        <td className="px-3 py-2.5 font-mono text-xs text-ink-primary">{ev.event_type}</td>
                        <td className="px-3 py-2.5"><SeverityBadge severity={ev.severity} /></td>
                      </tr>
                      {expanded && (
                        <tr key={`${ev.id}-detail`}>
                          <td colSpan={5} className="bg-base-bg px-6 py-3">
                            <JsonView data={ev.raw_payload} collapsedLabel="Raw payload" />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          )}

          {data.items.length > 0 && (
            <div className="flex items-center justify-between border-t border-base-border px-4 py-3 text-xs text-ink-muted">
              <span className="mono-tabular">
                {offset + 1}–{offset + data.items.length} · total {data.total}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                  className="flex items-center gap-1 rounded border border-base-border-strong px-2 py-1 hover:text-ink-primary disabled:opacity-40"
                >
                  <ChevronLeft size={14} /> Prev
                </button>
                <button
                  disabled={!data.has_more}
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
          <option key={opt} value={opt}>{opt === "" ? "All" : opt}</option>
        ))}
      </select>
    </label>
  );
}

function TextInput({ label, value, placeholder, onChange, type = "text" }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-ink-muted">
      {label}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-base-border-strong bg-base-bg px-2.5 py-1.5 text-sm text-ink-primary placeholder:text-ink-muted"
      />
    </label>
  );
}
