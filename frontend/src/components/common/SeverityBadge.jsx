// FILE LOCATION: frontend/src/components/common/SeverityBadge.jsx
const STYLES = {
  info: "bg-severity-info/15 text-severity-info border-severity-info/30",
  low: "bg-severity-low/15 text-severity-low border-severity-low/30",
  medium: "bg-severity-medium/15 text-severity-medium border-severity-medium/30",
  high: "bg-severity-high/15 text-severity-high border-severity-high/30",
  critical: "bg-severity-critical/15 text-severity-critical border-severity-critical/30",
};

export default function SeverityBadge({ severity, size = "sm" }) {
  const style = STYLES[severity] || STYLES.info;
  const sizeClass = size === "lg" ? "text-sm px-2.5 py-1" : "text-xs px-2 py-0.5";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border font-mono uppercase tracking-wide ${style} ${sizeClass}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {severity}
    </span>
  );
}
