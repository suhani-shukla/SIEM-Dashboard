// FILE LOCATION: frontend/src/components/common/States.jsx
export function LoadingState({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-ink-muted">
      <span className="h-3 w-3 animate-pulse-dot rounded-full bg-brand" />
      <span className="font-mono text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-base-border py-16 text-center">
      <p className="text-sm font-medium text-ink-secondary">{title}</p>
      {description && <p className="max-w-sm text-xs text-ink-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function InlineError({ message, onRetry }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-severity-critical/30 bg-severity-critical/10 px-4 py-3">
      <p className="text-sm text-severity-critical">{message || "Something went wrong."}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 rounded border border-severity-critical/40 px-2.5 py-1 text-xs text-severity-critical hover:bg-severity-critical/10"
        >
          Retry
        </button>
      )}
    </div>
  );
}
