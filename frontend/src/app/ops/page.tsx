import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { Panel } from "@/components/ui/Panel";

export const revalidate = 30;

const STATUS_COLOR: Record<string, string> = {
  success: "text-up",
  skipped: "text-amber",
  failed: "text-down",
  running: "text-cyan",
};

export default async function OpsPage() {
  const [universe, runs] = await Promise.all([
    api.universe(),
    api.sourceRuns(60).catch(() => []),
  ]);

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Ingest Health</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          source_runs · last {runs.length}
        </span>
      </header>

      {runs.length === 0 ? (
        <Panel title="No runs yet">
          <p className="text-[11px] text-fg-dim">
            The scheduler hasn&apos;t run any jobs yet. Start it with{" "}
            <code>python -m ingest.scheduler</code>.
          </p>
        </Panel>
      ) : (
        <Panel title="Recent runs" tight>
          <table className="w-full text-[11px] tabular-nums">
            <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
              <tr>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Source</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Started</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Status</th>
                <th className="border-b border-border px-3 py-1.5 text-right font-medium">Rows</th>
                <th className="border-b border-border px-3 py-1.5 text-left font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r, idx) => (
                <tr key={`${r.source_name}-${r.started_at}-${idx}`} className="hover:bg-panel-2">
                  <td className="border-b border-border px-3 py-1.5">{r.source_name}</td>
                  <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                    {new Date(r.started_at).toLocaleString("en-US", { timeZone: "America/New_York" })}
                  </td>
                  <td className={`border-b border-border px-3 py-1.5 uppercase ${STATUS_COLOR[r.status] ?? ""}`}>
                    {r.status}
                  </td>
                  <td className="border-b border-border px-3 py-1.5 text-right">{r.rows_fetched}</td>
                  <td className="border-b border-border px-3 py-1.5 text-[10px] text-fg-faint">
                    {r.error_msg ? r.error_msg.split("\n")[0].slice(0, 80) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </Shell>
  );
}
