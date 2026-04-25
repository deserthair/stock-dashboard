import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { BriefingFilteredView } from "@/components/briefing/BriefingFilteredView";
import { OvernightSynthesis } from "@/components/briefing/OvernightSynthesis";

export const revalidate = 60;

export default async function BriefingPage() {
  const briefing = await api.briefing();

  const when = new Date(briefing.generated_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Shell universe={briefing.universe}>
      <header className="mb-3 flex items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">
          Morning Briefing
        </h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          {when} · Pre-Market
        </span>
        <span className="ml-auto text-[11px] text-fg-dim">
          Next refresh <span className="text-accent">09:15 ET</span>
        </span>
      </header>

      <BriefingFilteredView
        stats={briefing.stats}
        events={briefing.events}
        universe={briefing.universe}
        macro={briefing.macro}
        upcomingEarnings={briefing.upcoming_earnings}
        synthesis={<OvernightSynthesis briefing={briefing.briefing} />}
      />
    </Shell>
  );
}
