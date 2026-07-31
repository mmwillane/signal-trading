import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info } from "@phosphor-icons/react";
import { api } from "../api/client";
import { num, pct, signedR, mt5Name } from "../lib/format";
import { Bezel, Eyebrow, SectionHeading } from "../components/ui";
import { Reveal } from "../components/Reveal";
import { Skeleton, ErrorState } from "../components/Skeleton";

const PERIODS = ["1y", "2y", "5y"];

export function Backtest() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api.settings() });
  const [symbol, setSymbol] = useState<string | null>(null);
  const [period, setPeriod] = useState("2y");

  const [trailing, setTrailing] = useState(true);
  const watch = settings.data?.watchlist ?? [];
  const active = symbol ?? watch[0] ?? null;

  const q = useQuery({
    queryKey: ["backtest", active, period, trailing],
    queryFn: () => api.backtest(active!, period, trailing),
    enabled: !!active,
  });

  return (
    <div className="space-y-7">
      <Reveal>
        <SectionHeading
          eyebrow="Validation historique"
          title="Backtest"
          desc="Teste la logique de setup sur le passé. Rappel : les performances passées ne préjugent pas des résultats futurs."
        />
      </Reveal>

      {/* Sélecteurs */}
      <Reveal delay={60}>
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {watch.map((s) => (
              <Chip key={s} active={active === s} onClick={() => setSymbol(s)}>{mt5Name(s)}</Chip>
            ))}
          </div>
          <div className="flex gap-2 items-center flex-wrap">
            {PERIODS.map((p) => (
              <Chip key={p} active={period === p} onClick={() => setPeriod(p)}>{p}</Chip>
            ))}
            <span className="mx-1 h-5 w-px" style={{ backgroundColor: "var(--color-line)" }} />
            <Chip active={trailing} onClick={() => setTrailing(!trailing)}>
              {trailing ? "Trailing ON" : "Trailing OFF"}
            </Chip>
          </div>
        </div>
      </Reveal>

      {q.isLoading && <Skeleton className="h-64 w-full" />}
      {q.isError && <ErrorState message={(q.error as Error).message} />}

      {q.data && q.data.status === "ok" && (
        <>
          <Reveal delay={80}>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
              <Stat label="Trades" value={String(q.data.stats.n_trades)} />
              <Stat label="Win rate" value={pct(q.data.stats.win_rate * 100, false)} tone={q.data.stats.win_rate >= 0.5 ? "up" : undefined} />
              <Stat
                label="Profit factor"
                value={q.data.stats.profit_factor === null ? "∞" : num(q.data.stats.profit_factor, 2)}
                tone={(q.data.stats.profit_factor ?? 99) >= 1 ? "up" : "down"}
              />
              <Stat label="R/R moyen" value={num(q.data.stats.avg_rr, 2)} tone={q.data.stats.avg_rr >= 0 ? "up" : "down"} />
              <Stat label="Drawdown max" value={`${num(q.data.stats.max_drawdown_r, 2)} R`} tone="down" />
              <Stat label="Résultat total" value={signedR(q.data.stats.total_r)} tone={q.data.stats.total_r >= 0 ? "up" : "down"} />
            </div>
          </Reveal>

          {q.data.equity_curve.length > 1 && (
            <Reveal delay={120}>
              <Bezel className="p-4">
                <Eyebrow>Courbe d'équité (R cumulés)</Eyebrow>
                <div className="mt-3">
                  <EquityCurve data={q.data.equity_curve} />
                </div>
              </Bezel>
            </Reveal>
          )}

          <Reveal delay={140}>
            <div className="flex items-start gap-2 rounded-2xl p-3 text-[12px]" style={{ backgroundColor: "rgba(139,124,246,0.06)", color: "#b3a9f7" }}>
              <Info size={16} weight="light" className="shrink-0 mt-0.5" />
              <span>Le backtest teste exactement la logique de setup utilisée pour les propositions live, avec une hypothèse de sortie prudente (stop prioritaire).</span>
            </div>
          </Reveal>
        </>
      )}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="press rounded-full px-4 py-2 text-sm font-medium transition-all duration-500"
      style={{
        backgroundColor: active ? "rgba(52,211,153,0.14)" : "rgba(255,255,255,0.03)",
        color: active ? "#5be0ae" : "var(--color-muted)",
        border: `1px solid ${active ? "rgba(52,211,153,0.3)" : "var(--color-line)"}`,
      }}
    >
      {children}
    </button>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  const color = tone === "up" ? "#5be0ae" : tone === "down" ? "#ff8497" : "var(--color-text)";
  return (
    <Bezel className="p-4">
      <div className="eyebrow">{label}</div>
      <div className="mt-1.5 text-2xl font-semibold tabular-nums" style={{ color, fontFamily: "var(--font-display)" }}>
        {value}
      </div>
    </Bezel>
  );
}

function EquityCurve({ data }: { data: { i: number; r: number }[] }) {
  const { path, area, zeroY, w, h } = useMemo(() => {
    const w = 320, h = 120, pad = 4;
    const rs = data.map((d) => d.r);
    const min = Math.min(0, ...rs);
    const max = Math.max(0, ...rs);
    const span = max - min || 1;
    const stepX = w / (data.length - 1);
    const y = (r: number) => h - pad - ((r - min) / span) * (h - pad * 2);
    const pts = data.map((d, i) => [i * stepX, y(d.r)]);
    const path = pts.map(([x, yy], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${yy.toFixed(1)}`).join(" ");
    const area = `${path} L${w},${h} L0,${h} Z`;
    return { path, area, zeroY: y(0), w, h };
  }, [data]);

  const last = data[data.length - 1].r;
  const color = last >= 0 ? "#34d399" : "#fb5a72";

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[120px] lg:h-[240px]" preserveAspectRatio="none">
      <defs>
        <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <line x1="0" y1={zeroY} x2={w} y2={zeroY} stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 3" />
      <path d={area} fill="url(#eq)" />
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
