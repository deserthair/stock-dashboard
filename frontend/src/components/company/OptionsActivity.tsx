import type { OptionsSummary } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { StatTile } from "@/components/ui/StatTile";
import { directionClass, fmtPct } from "@/lib/format";

function Sparkline({
  data,
  color = "#5cd5ff",
  height = 80,
  width = 520,
}: {
  data: { x: number; y: number }[];
  color?: string;
  height?: number;
  width?: number;
}) {
  if (data.length === 0) return <div className="h-20 w-full bg-panel-2" />;
  const xs = data.map((d) => d.x);
  const ys = data.map((d) => d.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const xR = xMax - xMin || 1;
  const yR = yMax - yMin || 1;
  const pad = { top: 4, right: 4, bottom: 4, left: 4 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const points = data
    .map((d) => {
      const x = pad.left + ((d.x - xMin) / xR) * plotW;
      const y = pad.top + plotH - ((d.y - yMin) / yR) * plotH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
      <rect x={0} y={0} width={width} height={height} fill="var(--bg-panel-2)" />
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}

export function OptionsActivity({ data }: { data: OptionsSummary }) {
  if (!data.latest) {
    return (
      <Panel title="Options Activity" meta="YFINANCE" tight>
        <div className="px-3 py-8 text-center text-[11px] text-fg-faint">
          No options snapshots for {data.ticker}. Run{" "}
          <code>python -m ingest.sources.options</code>.
        </div>
      </Panel>
    );
  }

  const iv = data.latest.atm_iv ?? null;
  const pc = data.latest.put_call_volume_ratio ?? null;
  const ivTrend = data.iv_trend_30d_pct;
  const pcTrend = data.pc_vol_trend_30d_pct;

  const ivSeries = data.history
    .filter((h) => h.atm_iv !== null)
    .map((h, i) => ({ x: i, y: (h.atm_iv as number) * 100 }));
  const pcSeries = data.history
    .filter((h) => h.put_call_volume_ratio !== null)
    .map((h, i) => ({ x: i, y: h.put_call_volume_ratio as number }));

  return (
    <div className="space-y-3">
      <Panel title="Options Activity" meta={`EXPIRY ${data.latest.expiry ?? "—"}`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="ATM IV"
            value={iv !== null ? `${(iv * 100).toFixed(1)}%` : "—"}
            valueClass={(ivTrend ?? 0) > 5 ? "text-amber" : "text-fg"}
            delta={
              ivTrend !== null ? (
                <span className={directionClass(ivTrend)}>
                  30d {fmtPct(ivTrend, { digits: 1 })}
                </span>
              ) : (
                "—"
              )
            }
          />
          <StatTile
            label="Put/Call Volume"
            value={pc !== null ? pc.toFixed(2) : "—"}
            valueClass={(pc ?? 0) > 1 ? "text-down" : (pc ?? 0) < 0.7 ? "text-up" : "text-amber"}
            delta={
              pcTrend !== null ? (
                <span className={directionClass(pcTrend)}>
                  30d {fmtPct(pcTrend, { digits: 1 })}
                </span>
              ) : (
                "—"
              )
            }
          />
          <StatTile
            label="Call Volume"
            value={(data.latest.total_call_volume ?? 0).toLocaleString()}
            delta={`OI ${(data.latest.total_call_oi ?? 0).toLocaleString()}`}
          />
          <StatTile
            label="Put Volume"
            value={(data.latest.total_put_volume ?? 0).toLocaleString()}
            delta={`OI ${(data.latest.total_put_oi ?? 0).toLocaleString()}`}
          />
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Panel title="ATM IV Trend · 60d" meta="ANNUALIZED" tight>
          <div className="p-3">
            <Sparkline
              data={ivSeries}
              color={(ivTrend ?? 0) > 0 ? "#ffb547" : "#5cd5ff"}
              height={80}
            />
            <div className="mt-2 text-[10px] text-fg-faint">
              A rising IV into earnings means the market expects a bigger move.
            </div>
          </div>
        </Panel>

        <Panel title="Put/Call Ratio · 60d" meta="VOLUME" tight>
          <div className="p-3">
            <Sparkline
              data={pcSeries}
              color={(pcTrend ?? 0) > 0 ? "#ff5c5c" : "#3fd97b"}
              height={80}
            />
            <div className="mt-2 text-[10px] text-fg-faint">
              Ratio &gt; 1 → more put than call volume (bearish). Rising trend
              ahead of earnings signals hedging / bearish positioning.
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
