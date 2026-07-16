// FILE LOCATION: frontend/src/components/common/StatusBadge.jsx
const STYLES = {
  new: "bg-brand/15 text-brand border-brand/30",
  acknowledged: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  investigating: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  resolved: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  false_positive: "bg-ink-muted/15 text-ink-muted border-ink-muted/30",
};

const LABELS = {
  new: "New",
  acknowledged: "Acknowledged",
  investigating: "Investigating",
  resolved: "Resolved",
  false_positive: "False positive",
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || STYLES.new;
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${style}`}>
      {LABELS[status] || status}
    </span>
  );
}
