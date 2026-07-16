// FILE LOCATION: frontend/src/components/common/JsonView.jsx
import { useState } from "react";
import { ChevronRight } from "lucide-react";

export default function JsonView({ data, collapsedLabel = "View raw JSON" }) {
  const [open, setOpen] = useState(false);

  if (data === null || data === undefined) {
    return <span className="text-ink-muted">—</span>;
  }

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 font-mono text-xs text-brand hover:text-brand-glow"
      >
        <ChevronRight size={14} className={`transition-transform ${open ? "rotate-90" : ""}`} />
        {open ? "Hide raw JSON" : collapsedLabel}
      </button>
      {open && (
        <pre className="mt-2 max-h-96 overflow-auto rounded border border-base-border bg-base-bg p-3 font-mono text-xs leading-relaxed text-ink-secondary">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
