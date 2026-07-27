import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Candle, LinePoint } from "../api/client";

// Graphique en chandeliers premium (lightweight-charts, TradingView).
export function PriceChart({
  candles,
  sma20,
  sma50,
  height = 300,
}: {
  candles: Candle[];
  sma20: LinePoint[];
  sma50: LinePoint[];
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9aa0ac",
        fontFamily: "Plus Jakarta Sans Variable, sans-serif",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: { borderColor: "rgba(255,255,255,0.08)", fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        vertLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: "#101218" },
        horzLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: "#101218" },
      },
      height,
      autoSize: true,
    });
    chartRef.current = chart;

    const toTime = (d: string) => (Date.parse(d) / 1000) as UTCTimestamp;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399",
      downColor: "#fb5a72",
      borderVisible: false,
      wickUpColor: "#2a9d78",
      wickDownColor: "#c14458",
    });
    candleSeries.setData(candles.map((c) => ({ ...c, time: toTime(c.time) })));

    const s20 = chart.addSeries(LineSeries, {
      color: "rgba(139,124,246,0.9)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    s20.setData(sma20.map((p) => ({ time: toTime(p.time), value: p.value })));

    const s50 = chart.addSeries(LineSeries, {
      color: "rgba(245,196,81,0.75)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    s50.setData(sma50.map((p) => ({ time: toTime(p.time), value: p.value })));

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [candles, sma20, sma50, height]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
