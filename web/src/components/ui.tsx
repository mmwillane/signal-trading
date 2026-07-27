import type { ReactNode } from "react";
import type { Tone } from "../lib/format";

// Double-bezel : coque extérieure machinée + cœur intérieur concentrique.
export function Bezel({
  children,
  className = "",
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <div className={`bezel ${onClick ? "press cursor-pointer" : ""}`} onClick={onClick}>
      <div className={`bezel-core ${className}`}>{children}</div>
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <span className="eyebrow inline-flex items-center gap-2 rounded-full px-3 py-1 hairline">
      {children}
    </span>
  );
}

const toneStyles: Record<Tone | "buy" | "sell", { bg: string; fg: string; dot: string }> = {
  up: { bg: "rgba(52,211,153,0.12)", fg: "#5be0ae", dot: "var(--color-emerald)" },
  down: { bg: "rgba(251,90,114,0.12)", fg: "#ff8497", dot: "var(--color-rose)" },
  flat: { bg: "rgba(245,196,81,0.12)", fg: "#f5c451", dot: "var(--color-amber)" },
  buy: { bg: "rgba(52,211,153,0.12)", fg: "#5be0ae", dot: "var(--color-emerald)" },
  sell: { bg: "rgba(251,90,114,0.12)", fg: "#ff8497", dot: "var(--color-rose)" },
};

export function Pill({
  tone = "flat",
  children,
  dot = false,
}: {
  tone?: Tone | "buy" | "sell";
  children: ReactNode;
  dot?: boolean;
}) {
  const s = toneStyles[tone];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{ backgroundColor: s.bg, color: s.fg }}
    >
      {dot && (
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: s.dot }} />
      )}
      {children}
    </span>
  );
}

function confidenceColor(score: number): string {
  if (score >= 75) return "#34d399";
  if (score >= 60) return "#8bd47f";
  if (score >= 45) return "#f5c451";
  return "#fb5a72";
}

/** Anneau de confiance 0-100. */
export function ConfidenceRing({ score, size = 44 }: { score: number; size?: number }) {
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const color = confidenceColor(score);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.32,0.72,0,1)" }}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-[11px] font-semibold tabular-nums"
        style={{ color, fontFamily: "var(--font-display)" }}
      >
        {score}
      </span>
    </div>
  );
}

/** Barre de confiance horizontale compacte. */
export function ConfidenceBar({ score }: { score: number }) {
  const color = confidenceColor(score);
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className="eyebrow">Confiance</span>
        <span className="text-xs font-semibold tabular-nums" style={{ color, fontFamily: "var(--font-display)" }}>
          {score}/100
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.07)" }}>
        <div
          className="h-full rounded-full"
          style={{ width: `${score}%`, backgroundColor: color, transition: "width 0.8s cubic-bezier(0.32,0.72,0,1)" }}
        />
      </div>
    </div>
  );
}

/** Badge LIVE / différé. */
export function LiveBadge({ live }: { live: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
      style={{
        backgroundColor: live ? "rgba(52,211,153,0.12)" : "rgba(255,255,255,0.05)",
        color: live ? "#5be0ae" : "var(--color-faint)",
      }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${live ? "live-dot" : ""}`}
        style={{ backgroundColor: live ? "var(--color-emerald)" : "var(--color-faint)" }}
      />
      {live ? "Live" : "Différé"}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  desc,
}: {
  eyebrow: string;
  title: string;
  desc?: string;
}) {
  return (
    <div className="space-y-3">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2
        className="text-3xl sm:text-4xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {title}
      </h2>
      {desc && <p className="text-[15px] leading-relaxed max-w-xl" style={{ color: "var(--color-muted)" }}>{desc}</p>}
    </div>
  );
}
