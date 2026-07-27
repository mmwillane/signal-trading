import { useMemo } from "react";

// Sparkline SVG légère (pas de dépendance de graphique pour la liste).
export function Sparkline({
  data,
  tone,
  width = 96,
  height = 34,
}: {
  data: number[];
  tone: "up" | "down" | "flat";
  width?: number;
  height?: number;
}) {
  const { path, area, id } = useMemo(() => {
    const id = `sp-${Math.random().toString(36).slice(2, 8)}`;
    if (!data || data.length < 2) return { path: "", area: "", id };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const span = max - min || 1;
    const step = width / (data.length - 1);
    const pts = data.map((v, i) => [i * step, height - ((v - min) / span) * (height - 4) - 2]);
    const path = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    const area = `${path} L${width},${height} L0,${height} Z`;
    return { path, area, id };
  }, [data, width, height]);

  const color =
    tone === "up" ? "#34d399" : tone === "down" ? "#fb5a72" : "#f5c451";

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {area && <path d={area} fill={`url(#${id})`} />}
      {path && <path d={path} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
  );
}
