import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { EventFeed } from "@/components/briefing/EventFeed";
import { MacroSignals } from "@/components/briefing/MacroSignals";
import { OvernightSynthesis } from "@/components/briefing/OvernightSynthesis";
import { StatRow } from "@/components/briefing/StatRow";
import { UniverseMatrix } from "@/components/briefing/UniverseMatrix";
import { UpcomingEarningsTable } from "@/components/briefing/UpcomingEarningsTable";

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

      <StatRow stats={briefing.stats} />

      <div className="mb-3 grid grid-cols-1 gap-3 xl:grid-cols-[2fr_1fr]">
        <OvernightSynthesis briefing={briefing.briefing} />
        <EventFeed events={briefing.events} />
      </div>

      <UniverseMatrix rows={briefing.universe} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <MacroSignals rows={briefing.macro} />
        <UpcomingEarningsTable rows={briefing.upcoming_earnings} />
      </div>
    </Shell>
  );
}
