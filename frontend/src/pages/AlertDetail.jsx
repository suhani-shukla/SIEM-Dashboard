// FILE LOCATION: frontend/src/pages/AlertDetail.jsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { api } from "../api/client";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import JsonView from "../components/common/JsonView";
import { LoadingState, InlineError } from "../components/common/States";

const VALID_TRANSITIONS = {
  new: ["acknowledged", "false_positive"],
  acknowledged: ["investigating", "false_positive", "resolved"],
  investigating: ["resolved", "false_positive", "acknowledged"],
  resolved: ["investigating"],
  false_positive: ["investigating"],
};

export default function AlertDetail() {
  const { id } = useParams();
  const [alert, setAlert] = useState(null);
  const [error, setError] = useState(null);
  const [note, setNote] = useState("");
  const [nextStatus, setNextStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setError(null);
    try {
      const data = await api.getAlert(id);
      setAlert(data);
      setNextStatus("");
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submitTransition() {
    if (!nextStatus) return;
    setSubmitting(true);
    try {
      await api.updateAlertStatus(id, { status: nextStatus, changed_by: "console-user", note: note || undefined });
      setNote("");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (error) return <InlineError message={error} onRetry={load} />;
  if (!alert) return <LoadingState label="Loading alert…" />;

  const options = VALID_TRANSITIONS[alert.status] || [];
  const eventWindow = buildEventWindowLink(alert);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link to="/alerts" className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary">
        <ArrowLeft size={14} /> Back to alerts
      </Link>

      {/* Header */}
      <div className="rounded-lg border border-base-border bg-base-surface p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-ink-primary">{alert.rule_name}</h2>
            <p className="mt-1 font-mono text-xs text-ink-muted">
              {alert.mitre_technique || "—"} · entity: {alert.entity || "—"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <SeverityBadge severity={alert.severity} size="lg" />
            <StatusBadge status={alert.status} />
          </div>
        </div>
        {alert.summary && <p className="mt-3 text-sm text-ink-secondary">{alert.summary}</p>}
        <p className="mt-3 font-mono text-xs text-ink-muted">
          Triggered {new Date(alert.triggered_at).toLocaleString()}
        </p>
        {eventWindow && (
          <Link
            to={eventWindow}
            className="mt-3 inline-flex items-center gap-1.5 text-xs text-brand hover:text-brand-glow"
          >
            View surrounding log activity <ExternalLink size={12} />
          </Link>
        )}
      </div>

      {/* Lifecycle control */}
      <div className="rounded-lg border border-base-border bg-base-surface p-5">
        <h3 className="mb-3 text-sm font-medium text-ink-secondary">Update status</h3>
        {options.length === 0 ? (
          <p className="text-xs text-ink-muted">No further transitions available from this state.</p>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => setNextStatus(opt)}
                  className={`rounded border px-3 py-1.5 text-xs font-medium transition-colors ${
                    nextStatus === opt
                      ? "border-brand bg-brand/10 text-brand"
                      : "border-base-border-strong text-ink-secondary hover:border-brand/40 hover:text-brand"
                  }`}
                >
                  {opt.replace("_", " ")}
                </button>
              ))}
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Optional note for the audit trail…"
              rows={2}
              className="w-full rounded border border-base-border-strong bg-base-bg px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted"
            />
            <button
              onClick={submitTransition}
              disabled={!nextStatus || submitting}
              className="rounded bg-brand px-4 py-2 text-xs font-semibold text-base-bg hover:bg-brand-glow disabled:opacity-50"
            >
              {submitting ? "Updating…" : `Move to ${nextStatus || "…"}`}
            </button>
          </div>
        )}
      </div>

      {/* History timeline */}
      <div className="rounded-lg border border-base-border bg-base-surface p-5">
        <h3 className="mb-3 text-sm font-medium text-ink-secondary">Status history</h3>
        {alert.history.length === 0 ? (
          <p className="text-xs text-ink-muted">No transitions recorded yet.</p>
        ) : (
          <ol className="space-y-3 border-l border-base-border pl-4">
            {alert.history.map((h) => (
              <li key={h.id} className="relative text-xs">
                <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-brand" />
                <p className="text-ink-primary">
                  <span className="font-medium">{h.from_status}</span> → <span className="font-medium">{h.to_status}</span>
                  <span className="text-ink-muted"> by {h.changed_by}</span>
                </p>
                <p className="font-mono text-ink-muted">{new Date(h.changed_at).toLocaleString()}</p>
                {h.note && <p className="mt-1 text-ink-secondary">{h.note}</p>}
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* Matched events */}
      <div className="rounded-lg border border-base-border bg-base-surface p-5">
        <h3 className="mb-3 text-sm font-medium text-ink-secondary">
          Matched events ({alert.matched_events.length})
        </h3>
        {alert.matched_events.length === 0 ? (
          <p className="text-xs text-ink-muted">No matched events recorded.</p>
        ) : (
          <div className="space-y-2">
            {alert.matched_events.map((ev) => (
              <div key={ev.id} className="rounded border border-base-border bg-base-bg p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-xs text-ink-secondary">{ev.event_type}</span>
                  <span className="font-mono text-xs text-ink-muted">
                    {new Date(ev.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="mt-2">
                  <JsonView data={ev.raw_payload} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function buildEventWindowLink(alert) {
  if (!alert.triggered_at) return null;
  const triggered = new Date(alert.triggered_at);
  const from = new Date(triggered.getTime() - 15 * 60_000).toISOString();
  const to = new Date(triggered.getTime() + 15 * 60_000).toISOString();
  const params = new URLSearchParams({ date_from: from, date_to: to });
  if (alert.entity) params.set("q", alert.entity);
  return `/events?${params.toString()}`;
}
