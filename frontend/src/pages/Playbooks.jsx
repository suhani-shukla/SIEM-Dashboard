// FILE LOCATION: frontend/src/pages/Playbooks.jsx
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { LoadingState, InlineError, EmptyState } from "../components/common/States";

// The tactics relevant to the four shipped playbooks. Extend this if you add
// playbooks covering other tactics later.
const TACTICS = [
  { id: "credential-access", label: "Credential Access" },
  { id: "exfiltration", label: "Exfiltration" },
  { id: "initial-access", label: "Initial Access" },
  { id: "privilege-escalation", label: "Privilege Escalation" },
];

function tacticIdFor(playbook) {
  const t = (playbook.mitre_attack?.tactic || "").toLowerCase().replace(/\s+/g, "-");
  return t || "unknown";
}

export default function Playbooks() {
  const [playbooks, setPlaybooks] = useState(null);
  const [error, setError] = useState(null);
  const [busyName, setBusyName] = useState(null);

  async function load() {
    setError(null);
    try {
      const res = await api.listPlaybooks();
      setPlaybooks(res);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggle(name, enabled) {
    setBusyName(name);
    try {
      await api.togglePlaybook(name, enabled);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyName(null);
    }
  }

  if (error) return <InlineError message={error} onRetry={load} />;
  if (playbooks === null) return <LoadingState label="Loading playbooks…" />;
  if (playbooks.length === 0) {
    return <EmptyState title="No playbooks loaded" description="Add YAML playbooks to the /playbooks directory." />;
  }

  return (
    <div className="space-y-6">
      {/* Coverage grid — the signature element: covered cells glow */}
      <div className="rounded-lg border border-base-border bg-base-surface p-5">
        <h2 className="mb-4 text-sm font-medium text-ink-secondary">MITRE ATT&CK coverage</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {TACTICS.map((tactic) => {
            const covering = playbooks.filter((p) => tacticIdFor(p) === tactic.id);
            const covered = covering.length > 0;
            const anyEnabled = covering.some((p) => p.enabled);
            return (
              <div
                key={tactic.id}
                className={`rounded-lg border p-4 transition-shadow ${
                  covered
                    ? anyEnabled
                      ? "border-brand/40 bg-brand/5 shadow-glow"
                      : "border-base-border-strong bg-base-hover"
                    : "border-dashed border-base-border bg-base-bg opacity-50"
                }`}
              >
                <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{tactic.label}</p>
                {covered ? (
                  <div className="mt-2 space-y-1">
                    {covering.map((p) => (
                      <p key={p.name} className="font-mono text-xs text-ink-primary">
                        {p.mitre_attack?.technique_id} — {p.mitre_attack?.technique_name}
                      </p>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-ink-muted">No playbook coverage</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Playbook list */}
      <div className="overflow-hidden rounded-lg border border-base-border bg-base-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-base-border bg-base-surface-raised text-xs uppercase tracking-wide text-ink-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Playbook</th>
              <th className="px-4 py-3 font-medium">Rule type</th>
              <th className="px-4 py-3 font-medium">MITRE technique</th>
              <th className="px-4 py-3 font-medium">Tactic</th>
              <th className="px-4 py-3 font-medium">Enabled</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-base-border">
            {playbooks.map((p) => (
              <tr key={p.name} className="hover:bg-base-hover">
                <td className="px-4 py-3">
                  <p className="font-medium text-ink-primary">{p.name}</p>
                  {p.description && <p className="text-xs text-ink-muted">{p.description}</p>}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{p.rule_type}</td>
                <td className="px-4 py-3 font-mono text-xs text-ink-secondary">
                  {p.mitre_attack?.technique_id} — {p.mitre_attack?.technique_name}
                </td>
                <td className="px-4 py-3 text-xs text-ink-secondary">{p.mitre_attack?.tactic}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggle(p.name, !p.enabled)}
                    disabled={busyName === p.name}
                    className={`relative h-5 w-9 rounded-full transition-colors disabled:opacity-50 ${
                      p.enabled ? "bg-brand" : "bg-base-border-strong"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-base-bg transition-transform ${
                        p.enabled ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
