import type { Flag } from "../types";

type Props = { flags: Flag[] };

export function AlertsTab({ flags }: Props) {
  if (!flags.length) {
    return <div className="alert alert-success">No alerts — your data looks good.</div>;
  }

  return (
    <div>
      {flags.map((flag, i) => (
        <div key={i} className={`alert alert-${flag.level === "error" ? "error" : flag.level === "warning" ? "warning" : "info"}`}>
          {flag.message}
        </div>
      ))}
    </div>
  );
}
