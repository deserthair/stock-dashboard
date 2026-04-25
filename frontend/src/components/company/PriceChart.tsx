"use client";

import { useEffect, useRef, useState } from "react";
import {
  AreaSeries,
  ColorType,
  createChart,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

import type { ChartMarker, PriceBar } from "@/lib/types";

const SEVERITY_COLOR: Record<string, string> = {
  hi: "#ff5c5c",
  md: "#ffb547",
  lo: "#5cd5ff",
};
const SEVERITY_LABEL: Record<string, string> = {
  hi: "HI",
  md: "MD",
  lo: "LO",
};

export function PriceChart({
  bars,
  markers,
}: {
  bars: PriceBar[];
  markers: ChartMarker[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; marker: ChartMarker } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 240,
      layout: {
        background: { type: ColorType.Solid, color: "#161922" },
        textColor: "#737a88",
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "#232834", style: LineStyle.Dotted },
        horzLines: { color: "#232834", style: LineStyle.Dotted },
      },
      rightPriceScale: { borderColor: "#232834" },
      timeScale: { borderColor: "#232834", timeVisible: false, secondsVisible: false },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#c8e85a",
      topColor: "rgba(200, 232, 90, 0.32)",
      bottomColor: "rgba(200, 232, 90, 0.02)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    seriesRef.current = series;

    const resize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    const data = bars
      .filter((b) => b.close !== null)
      .map((b) => {
        const [y, m, d] = b.date.split("-").map(Number);
        return {
          time: (Date.UTC(y, m - 1, d) / 1000) as UTCTimestamp,
          value: b.close as number,
        };
      });
    seriesRef.current.setData(data);

    const sortedMarkers = [...markers].sort((a, b) => (a.date > b.date ? 1 : -1));
    const markerPayload = sortedMarkers.map((m) => {
      const [y, mo, d] = m.date.split("-").map(Number);
      return {
        time: (Date.UTC(y, mo - 1, d) / 1000) as UTCTimestamp,
        position: "aboveBar" as const,
        color: SEVERITY_COLOR[m.severity] ?? "#5cd5ff",
        shape: "circle" as const,
        text: SEVERITY_LABEL[m.severity] ?? "?",
      };
    });
    // Lightweight-charts v5 moves marker rendering into the `createSeriesMarkers`
    // primitive. Soft-load it to keep the bundle tight.
    void import("lightweight-charts").then((lc) => {
      if (seriesRef.current && (lc as any).createSeriesMarkers) {
        (lc as any).createSeriesMarkers(seriesRef.current, markerPayload);
      }
    });

    chartRef.current?.timeScale().fitContent();
  }, [bars, markers]);

  useEffect(() => {
    if (!chartRef.current || !seriesRef.current) return;
    const chart = chartRef.current;
    const series = seriesRef.current;

    const handler = (param: any) => {
      if (!param.point || !param.time) {
        setHover(null);
        return;
      }
      // Find a marker on the current hovered date.
      const iso = new Date((param.time as number) * 1000).toISOString().slice(0, 10);
      const match = markers.find((m) => m.date === iso);
      if (!match) {
        setHover(null);
        return;
      }
      setHover({ x: param.point.x, y: param.point.y, marker: match });
    };
    chart.subscribeCrosshairMove(handler);
    return () => chart.unsubscribeCrosshairMove(handler);
  }, [markers]);

  return (
    <div className="relative">
      <div ref={containerRef} className="h-60 w-full border border-border bg-panel-2" />
      {hover && (
        <div
          className="pointer-events-none absolute z-10 max-w-[260px] rounded-sm border border-border-hot bg-panel px-2.5 py-1.5 text-[10px] shadow-lg"
          style={{
            left: Math.min(hover.x + 12, 520),
            top: Math.max(hover.y - 50, 6),
          }}
        >
          <div className="mb-0.5 flex items-center gap-2 text-[10px] uppercase tracking-[0.1em]">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ background: SEVERITY_COLOR[hover.marker.severity] }}
            />
            <span className="text-fg-dim">
              {hover.marker.source ?? "EVENT"} · {hover.marker.severity.toUpperCase()}
            </span>
            <span className="ml-auto text-fg-faint">{hover.marker.date}</span>
          </div>
          <div className="text-fg">{hover.marker.description}</div>
        </div>
      )}
    </div>
  );
}
