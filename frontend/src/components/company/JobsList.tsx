import type { JobsSnapshotOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

export function JobsList({ items }: { items: JobsSnapshotOut[] }) {
  if (!items.length) {
    return (
      <Panel title="Jobs · Careers-page Snapshots" meta="ATS" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No jobs snapshots yet. The `jobs` worker runs weekly.
        </div>
      </Panel>
    );
  }
  const latest = items[0];
  return (
    <Panel
      title="Jobs · Careers-page Snapshots"
      meta={`${items.length} SNAPSHOTS`}
      tight
    >
      <div className="border-b border-border px-3 py-3">
        <div className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
          Latest ({latest.snapshot_date})
        </div>
        <div className="mt-1 font-serif text-[24px] font-medium">
          {latest.total_count ?? "—"}{" "}
          <span className="text-[11px] font-mono text-fg-dim">postings</span>
        </div>
        {latest.corporate_count !== null && (
          <div className="text-[11px] text-fg-dim">
            {latest.corporate_count} corporate / eng / tech
          </div>
        )}
        {Object.keys(latest.by_department ?? {}).length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-1 text-[11px] md:grid-cols-3">
            {Object.entries(latest.by_department as Record<string, number>)
              .sort((a, b) => Number(b[1]) - Number(a[1]))
              .slice(0, 9)
              .map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2 border-b border-border py-1">
                  <span className="truncate text-fg-dim">{k}</span>
                  <span className="tabular-nums">{String(v)}</span>
                </div>
              ))}
          </div>
        )}
      </div>

      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Date</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Total</th>
            <th className="border-b border-border px-3 py-1.5 text-right font-medium">Corporate</th>
          </tr>
        </thead>
        <tbody>
          {items.slice(1).map((j) => (
            <tr key={j.snapshot_date} className="hover:bg-panel-2">
              <td className="border-b border-border px-3 py-1.5">{j.snapshot_date}</td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {j.total_count ?? "—"}
              </td>
              <td className="border-b border-border px-3 py-1.5 text-right">
                {j.corporate_count ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
