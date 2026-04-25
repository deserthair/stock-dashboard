import type { EarningsPostmortemOut } from "@/lib/types";

function renderNarrative(text: string): string {
  return text
    .replace(/<tag>/g, '<span class="postmortem-tag">')
    .replace(/<\/tag>/g, "</span>");
}

export function PostmortemCard({ pm }: { pm: EarningsPostmortemOut }) {
  return (
    <div className="border border-border-hot border-l-[3px] border-l-accent bg-gradient-to-br from-[rgba(200,232,90,0.04)] via-transparent to-transparent px-4 py-3.5">
      <div className="mb-1.5 flex items-center gap-2 text-[10px] uppercase tracking-[0.15em] text-accent">
        <span>◆ Postmortem</span>
        <span className="text-fg-faint">
          {pm.fiscal_period ?? ""} · reported {pm.report_date}
        </span>
        <span className="ml-auto text-fg-faint">
          {pm.model === "seed:demo" ? "DEMO" : pm.model.toUpperCase()} ·{" "}
          {pm.token_count} tokens
        </span>
      </div>
      <div className="font-serif text-[16px] font-medium leading-tight text-fg">
        {pm.headline}
      </div>
      <div
        className="briefing-prose mt-2 text-fg"
        dangerouslySetInnerHTML={{ __html: renderNarrative(pm.narrative) }}
      />
      {pm.tags && pm.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {pm.tags.map((t) => (
            <span
              key={t}
              className="rounded-sm border border-border-hot bg-panel-2 px-1.5 py-0 text-[10px] text-fg-dim"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
