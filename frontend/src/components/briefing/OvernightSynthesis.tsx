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
      info={{
        title: "Overnight Synthesis",
        explanation:
          "A short pre-market briefing written by Claude (an AI assistant) every morning. It summarizes what happened overnight in the restaurant sector: the biggest story, what the broader economy is doing, where our predictive 'hypotheses' stand, and any red flags worth watching.\n\nThe AI is given a snapshot of all our data and asked to write four short sections. Tickers (like MCD, SBUX) are highlighted in green chips; bolded numbers are the key facts.\n\nIt's meant to replace skimming a dozen news sites — read this and you have the gist.",
      }}
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
