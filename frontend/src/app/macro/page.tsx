import { api } from "@/lib/api";
import { Shell } from "@/components/layout/Shell";
import { SeriesChart } from "@/components/macro/SeriesChart";
import { Panel } from "@/components/ui/Panel";
import { INFO } from "@/lib/info";

export const revalidate = 600;

const EXPOSURE: Record<string, string[]> = {
  PBEEFUSDM:     ["TXRH", "MCD", "CMG"],
  WPU0211:       ["WING", "CAVA", "QSR"],
  PWHEAMTUSDM:   ["DPZ", "CMG"],
  GASREGW:       ["ALL"],
  UMCSENT:       ["ALL"],
  CES7072200003: ["ALL"],
  UNRATE:        ["ALL"],
  DGS10:         ["ALL"],
};

const SERIES_ORDER = [
  "PBEEFUSDM",
  "WPU0211",
  "PWHEAMTUSDM",
  "GASREGW",
  "UMCSENT",
  "CES7072200003",
  "UNRATE",
  "DGS10",
];

const COLOR_BY_DIRECTION: Record<string, string> = {
  up: "#3fd97b",
  down: "#ff5c5c",
  flat: "#5cd5ff",
};

export default async function MacroPage() {
  const universe = await api.universe();
  const macro = await api.macro().catch(() => []);

  // Fetch all per-series observations in parallel; series that have no
  // observations stored (FRED ingest hasn't run) will just render empty.
  const details = await Promise.all(
    SERIES_ORDER.map((id) =>
      api.macroSeries(id, 365).catch(() => null),
    ),
  );

  return (
    <Shell universe={universe}>
      <header className="mb-3 flex items-baseline gap-4 border-b border-border pb-2">
        <h1 className="font-serif text-2xl font-medium tracking-tight">Macro</h1>
        <span className="text-[11px] uppercase tracking-[0.1em] text-fg-faint">
          FRED · 90-day trailing change on aggregate bars, 365d time series
        </span>
      </header>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {SERIES_ORDER.map((id, idx) => {
          const meta = macro.find((m) => m.series_id === id);
          const detail = details[idx];
          const exposure = EXPOSURE[id] ?? [];
          return (
            <Panel
              key={id}
              title={meta?.label ?? id}
              meta={id}
              info={{
                ...INFO.macro_series,
                title: meta?.label ?? id,
                pageContext: `series_id=${id}; exposure=${exposure.join(",")}; 90d_change=${meta?.change_label ?? "n/a"}`,
              }}
            >
              <div className="mb-2 flex items-baseline gap-3">
                <div
                  className={`font-serif text-[22px] font-medium leading-none tracking-tight ${
                    meta?.direction === "up"
                      ? "text-up"
                      : meta?.direction === "down"
                      ? "text-down"
                      : "text-fg"
                  }`}
                >
                  {meta?.change_label ?? "—"}
                </div>
                <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
                  90d change
                </span>
                <span className="ml-auto text-[10px] uppercase tracking-[0.1em] text-fg-dim">
                  Exposure: <span className="text-fg">{exposure.join(" · ") || "—"}</span>
                </span>
              </div>
              {detail && detail.observations.length > 1 ? (
                <SeriesChart
                  data={detail.observations}
                  color={COLOR_BY_DIRECTION[meta?.direction ?? "flat"]}
                />
              ) : (
                <div className="flex h-[140px] items-center justify-center border border-border bg-panel-2 text-fg-faint">
                  <span className="text-[11px] uppercase tracking-[0.15em]">
                    No observations yet — waiting for FRED worker
                  </span>
                </div>
              )}
            </Panel>
          );
        })}
      </div>
    </Shell>
  );
}
