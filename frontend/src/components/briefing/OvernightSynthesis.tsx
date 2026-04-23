import type { BriefingOut } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";

function renderBody(body: string): string {
  return body
    .replace(/<tag>/g, '<span class="tag">')
    .replace(/<\/tag>/g, "</span>");
}

export function OvernightSynthesis({ briefing }: { briefing: BriefingOut }) {
  const when = new Date(briefing.generated_at).toLocaleTimeString("en-US", {
    timeZone: "America/New_York",
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <Panel
      title="Overnight Synthesis"
      meta={`CLAUDE · ${briefing.token_count} TOKENS · ${when} ET`}
      tight
    >
      <div className="briefing-prose px-6 py-5 text-fg">
        {briefing.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="mb-2 mt-4 font-mono text-[11px] font-semibold uppercase tracking-[0.15em] text-accent first:mt-0">
              {section.heading}
            </h2>
            <p
              // Briefing bodies come from our own backend seeding — tags are
              // whitelisted (<tag>, <strong>) and the input is trusted.
              dangerouslySetInnerHTML={{ __html: renderBody(section.body) }}
            />
          </section>
        ))}
      </div>
    </Panel>
  );
}
