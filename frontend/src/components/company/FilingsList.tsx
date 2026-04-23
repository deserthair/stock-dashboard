import type { FilingOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function FilingsList({ items }: { items: FilingOut[] }) {
  if (!items.length) {
    return (
      <Panel title="SEC Filings" meta="EDGAR" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No filings ingested yet. The `filings` worker runs every 2 hours.
        </div>
      </Panel>
    );
  }
  return (
    <Panel title="SEC Filings" meta={`${items.length} FILINGS`} tight>
      <table className="w-full text-[11px] tabular-nums">
        <thead className="bg-panel-2 text-[10px] uppercase tracking-[0.1em] text-fg-faint">
          <tr>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Filed</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Form</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Items</th>
            <th className="border-b border-border px-3 py-1.5 text-left font-medium">Title</th>
          </tr>
        </thead>
        <tbody>
          {items.map((f) => (
            <tr key={f.filing_id} className="hover:bg-panel-2">
              <td className="border-b border-border px-3 py-1.5">{fmtDate(f.filed_at)}</td>
              <td className="border-b border-border px-3 py-1.5">
                <span
                  className={`rounded-sm border border-border-hot bg-panel-2 px-1.5 py-0 text-[10px] ${
                    f.filing_type === "8-K" ? "text-accent" : "text-fg"
                  }`}
                >
                  {f.filing_type}
                </span>
              </td>
              <td className="border-b border-border px-3 py-1.5 text-fg-dim">
                {f.item_numbers && f.item_numbers.length > 0
                  ? f.item_numbers.join(", ")
                  : "—"}
              </td>
              <td className="border-b border-border px-3 py-1.5">
                {f.primary_doc_url ? (
                  <a
                    href={f.primary_doc_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-fg hover:text-accent"
                  >
                    {f.title ?? f.filing_type}
                  </a>
                ) : (
                  <span>{f.title ?? f.filing_type}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
