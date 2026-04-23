"use client";

import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  LineSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

import type { MacroObservation } from "@/lib/types";

export function SeriesChart({
  data,
  color = "#5cd5ff",
  height = 140,
}: {
  data: MacroObservation[];
  color?: string;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#161922" },
        textColor: "#737a88",
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 9,
      },
      grid: {
        vertLines: { color: "#232834", style: LineStyle.Dotted },
        horzLines: { color: "#232834", style: LineStyle.Dotted },
      },
      rightPriceScale: { borderColor: "#232834" },
      timeScale: { borderColor: "#232834" },
    });
    chartRef.current = chart;
    const series = chart.addSeries(LineSeries, {
      color,
      lineWidth: 2,
      priceLineVisible: false,
    });
    seriesRef.current = series;

    const resize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, [color, height]);

  useEffect(() => {
    if (!seriesRef.current) return;
    const points = data
      .filter((o) => o.value !== null)
      .map((o) => {
        const [y, m, d] = o.date.split("-").map(Number);
        return {
          time: (Date.UTC(y, m - 1, d) / 1000) as UTCTimestamp,
          value: o.value as number,
        };
      });
    seriesRef.current.setData(points);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} className="w-full border border-border bg-panel-2" style={{ height }} />;
}
